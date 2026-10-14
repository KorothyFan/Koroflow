import { canonicalize, defineEndpoint, wakeAfter } from "@hypit/hypit/endpoint";
import type { AsyncEndpoint, BlobRef, CredentialRef, EndpointRequest, ResourceStore } from "@hypit/hypit/endpoint";
import {
  assertMappingCoversPorts,
  compileWireRequest,
  generationTypes,
  mappingSupportsRequest,
  sealGeneratedImageSet,
  sealGeneratedVideoSet,
  selectWireModelForRequest,
} from "@hypit/generation";
import type { GenerationRequest, GenerationWireMapping } from "@hypit/generation";
import { seedancePorts } from "@hypit/seedance";
import { gptImage2Ports } from "@hypit/gpt-image";

export const providerModule = { name: "@example/provider-haiyi", version: "1" } as const;
export const capability = {
  module: { name: "@hypit/seedance", version: "1" },
  name: "seedance-2.5",
} as const;
export const imageCapability = {
  module: { name: "@hypit/gpt-image", version: "1" },
  name: "gpt-image-2",
} as const;

const HAIYI_MODEL = "doubao-seedance-2-5-260628";
const HAIYI_PROVIDER = "volcengine";
const HAIYI_BASE = "https://art.huya.info";
const SUPPORTED_RESOLUTIONS = new Set(["480p", "720p"]);
const SUPPORTED_SECONDS = { min: 4, max: 30 };

export const mapping: GenerationWireMapping = {
  capability,
  result: "video",
  routes: [{ model: HAIYI_MODEL }],
  fields: {
    prompt: { as: "value", field: "prompt" },
    duration: { as: "value", field: "duration" },
    resolution: { as: "value", field: "resolution" },
    aspectRatio: { as: "value", field: "aspectRatio" },
    generateAudio: { as: "value", field: "generateAudio" },
    webSearch: { as: "value", field: "webSearch" },
    referenceImage: { as: "urlArray", field: "images", resourceFields: ["personReference"] },
    referenceVideo: { as: "urlArray", field: "video", resourceFields: ["personReference"] },
    referenceAudio: { as: "urlArray", field: "audio" },
    firstFrame: { as: "url", field: "firstFrame", resourceFields: ["personReference"] },
    lastFrame: { as: "url", field: "lastFrame", resourceFields: ["personReference"] },
  },
};

assertMappingCoversPorts(seedancePorts["seedance-2.5"], mapping);

export const imageMapping: GenerationWireMapping = {
  capability: imageCapability,
  result: "image",
  routes: [{ model: "gpt-image-2.5-flare" }],
  fields: {
    prompt: { as: "value", field: "prompt" },
    aspectRatio: { as: "value", field: "aspectRatio" },
    resolution: { as: "value", field: "resolution" },
    background: { as: "value", field: "background" },
    images: { as: "urlArray", field: "imageUrls" },
  },
};

assertMappingCoversPorts(gptImage2Ports, imageMapping);

function object(value: unknown, subject: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${subject} must be an object`);
  }
  return value as Record<string, unknown>;
}

function text(value: unknown, subject: string): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`${subject} must be non-empty text`);
  }
  return value;
}

function baseUrl(value: string | undefined): string {
  const candidate = value ?? HAIYI_BASE;
  const url = new URL(candidate);
  if (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname))) {
    throw new Error("Haiyi baseUrl must use HTTPS or loopback HTTP");
  }
  return url.href.replace(/\/$/u, "");
}

function publicFailure(value: unknown): { code: string; message: string } | undefined {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return undefined;
  const item = value as Record<string, unknown>;
  const code = item.code ?? item.error;
  const message = item.message ?? item.msg ?? item.detail;
  if (typeof code !== "string" && typeof message !== "string") return undefined;
  return {
    code: typeof code === "string" ? code : "HAIYI_ERROR",
    message: typeof message === "string"
      ? message.replace(/https?:\/\/\S+/giu, "[redacted-url]")
      : "Haiyi request failed",
  };
}

function nestedObject(value: Record<string, unknown>, key: string): Record<string, unknown> | undefined {
  const nested = value[key];
  return nested !== null && typeof nested === "object" && !Array.isArray(nested)
    ? nested as Record<string, unknown>
    : undefined;
}

function findString(value: unknown, keys: readonly string[]): string | undefined {
  if (value === null || typeof value !== "object") return typeof value === "string" ? value : undefined;
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = findString(item, keys);
      if (found !== undefined) return found;
    }
    return undefined;
  }
  const record = value as Record<string, unknown>;
  for (const key of keys) {
    if (typeof record[key] === "string" && record[key].length > 0) return record[key];
  }
  for (const key of ["data", "result", "output", "results"]) {
    const found = findString(record[key], keys);
    if (found !== undefined) return found;
  }
  return undefined;
}

function findUrls(value: unknown): string[] {
  if (typeof value === "string") return /^https?:\/\//u.test(value) ? [value] : [];
  if (value === null || typeof value !== "object") return [];
  if (Array.isArray(value)) return value.flatMap(findUrls);
  const record = value as Record<string, unknown>;
  const directKeys = ["url", "video_url", "videoUrl", "file_url", "fileUrl", "download_url", "downloadUrl", "src", "uri"];
  const direct = directKeys.flatMap((key) => typeof record[key] === "string" ? [record[key] as string] : []);
  if (direct.length > 0) return direct;
  return ["data", "result", "output", "results"].flatMap((key) => findUrls(record[key]));
}

function isPersonReference(request: GenerationRequest): boolean {
  for (const name of ["referenceImage", "referenceVideo", "firstFrame", "lastFrame"]) {
    for (const item of request.ports[name] ?? []) {
      if (typeof item === "object" && item.fields?.personReference === true) return true;
    }
  }
  return false;
}

function modeOf(request: GenerationRequest): "text2video" | "image2video" {
  return request.ports.firstFrame !== undefined
    || request.ports.referenceImage !== undefined
    || request.ports.referenceVideo !== undefined
    || request.ports.referenceAudio !== undefined
    ? "image2video"
    : "text2video";
}

function normalizeParameters(input: Record<string, unknown>, request: GenerationRequest): Record<string, unknown> {
  const first = input.firstFrame;
  const last = input.lastFrame;
  const parameters: Record<string, unknown> = { ...input };
  delete parameters.firstFrame;
  delete parameters.lastFrame;

  if (first !== undefined) {
    parameters.images = [
      first,
      ...(last === undefined ? [] : [last]),
    ];
    parameters.roleMode = "frame";
  } else if (request.ports.referenceImage !== undefined
    || request.ports.referenceVideo !== undefined
    || request.ports.referenceAudio !== undefined) {
    parameters.roleMode = "reference";
  }

  const webSearch = parameters.webSearch;
  delete parameters.webSearch;
  if (webSearch === true) parameters.mcpList = ["web_search"];

  parameters.nsfw = false;
  parameters.output_format = "mp4";
  parameters.isUploadAsset = isPersonReference(request);
  return parameters;
}

function normalizeImageParameters(input: Record<string, unknown>): Record<string, unknown> {
  const parameters = { ...input };
  const resolution = parameters.resolution;
  if (typeof resolution === "string") parameters.resolution = resolution.toLowerCase();
  return parameters;
}

function responsePayload(value: unknown): Record<string, unknown> {
  const record = object(value, "Haiyi response");
  const data = nestedObject(record, "data");
  return data === undefined ? record : { ...record, ...data };
}

export function createHaiyiProvider(options: {
  instance: string;
  pool: string;
  baseUrl?: string;
  apiKey: CredentialRef;
  defaultConcurrency?: number;
  pollIntervalMs?: number;
  requestTimeoutMs?: number;
  actionLimits?: import("@hypit/hypit/endpoint").EndpointActionLimits;
  fetch?: typeof globalThis.fetch;
}) {
  const base = baseUrl(options.baseUrl);
  const fetcher = options.fetch ?? globalThis.fetch;
  const interval = options.pollIntervalMs ?? 5_000;
  const timeout = options.requestTimeoutMs ?? 120_000;
  const key = (credentials: Readonly<Record<string, { secret: string }>>) => text(credentials.apiKey?.secret, "Haiyi API token");

  async function request(
    path: string,
    credentials: Readonly<Record<string, { secret: string }>>,
    init: RequestInit = {},
  ): Promise<Record<string, unknown>> {
    const response = await fetcher(`${base}${path}`, {
      ...init,
      headers: { authorization: `Bearer ${key(credentials)}`, ...init.headers },
      signal: AbortSignal.timeout(timeout),
    });
    const raw = await response.text();
    let parsed: unknown;
    try { parsed = raw.length === 0 ? {} : JSON.parse(raw); } catch { parsed = { message: raw.slice(0, 400) }; }
    if (!response.ok) {
      const failure = publicFailure(parsed);
      throw Object.assign(new Error(
        `Haiyi ${init.method ?? "GET"} ${path} returned HTTP ${response.status}`
        + (failure === undefined ? "" : `; ${failure.code}: ${failure.message}`),
      ), failure === undefined ? {} : { code: failure.code });
    }
    return responsePayload(parsed);
  }

  async function upload(
    artifact: BlobRef,
    resources: ResourceStore,
    credentials: Readonly<Record<string, { secret: string }>>,
  ) {
    const bytes = await resources.get(artifact.resource);
    if (bytes === undefined) throw new Error(`Haiyi reference resource ${artifact.resource} is unavailable`);
    const form = new FormData();
    form.append("file", new Blob([new Uint8Array(bytes)], { type: artifact.mediaType }), artifact.resource.split("/").pop() ?? "asset");
    const result = await request("/openapi/v1/file/upload", credentials, { method: "POST", body: form });
    const url = findString(result, ["url", "file_url", "fileUrl", "download_url", "downloadUrl"]);
    if (url === undefined) throw new Error("Haiyi upload did not return a usable URL");
    return url;
  }

  const videoEndpoint: AsyncEndpoint = {
    async start(context) {
      const authored = context.need.constraints as unknown as GenerationRequest;
      const support = serviceSupport(context.need);
      if (support.status === "unsupported") throw new Error(support.reason);
      const model = selectWireModelForRequest(mapping, authored);
      await context.reportProgress?.({ phase: `Preparing Haiyi request: ${model}` });
      const wire = await compileWireRequest(mapping, authored, async (artifact) =>
        await upload(artifact, context.resources, context.credentials));
      const operation = modeOf(authored);
      const body = {
        model: { provider: HAIYI_PROVIDER, model: HAIYI_MODEL, type: operation },
        parameters: normalizeParameters(wire.input as Record<string, unknown>, authored),
      };
      await context.reportProgress?.({ phase: `Submitting Haiyi request: ${operation}` });
      const submitted = await request("/openapi/v1/generate/video",
        context.credentials, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const taskId = findString(submitted, ["task_id", "taskId", "id"]);
      if (taskId === undefined) throw new Error("Haiyi submission did not return task_id");
      const handle = { taskId };
      const receipt = { id: taskId };
      await context.checkpoint?.({ handle, receipt });
      return { ...wakeAfter(handle, interval), receipt };
    },
    async poll(context) {
      const taskId = text(object(context.handle, "Haiyi handle").taskId, "Haiyi task id");
      const result = await request(`/openapi/v1/generate/result/${encodeURIComponent(taskId)}`, context.credentials);
      const status = text(result.status ?? nestedObject(result, "data")?.status, "Haiyi task status").toLowerCase();
      if (["pending", "queued", "running", "processing", "created"].includes(status)) {
        return wakeAfter({ taskId }, interval, Date.now(), { phase: status });
      }
      if (["fail", "failed", "error", "cancelled", "canceled"].includes(status)) {
        const failure = publicFailure(result) ?? { code: "HAIYI_TASK_FAILED", message: `Haiyi task ${taskId} failed` };
        return { status: "failed", receipt: { id: taskId }, failure: { code: failure.code, message: failure.message } };
      }
      if (status !== "success" && status !== "succeeded" && status !== "completed" && status !== "ready") {
        throw new Error(`Haiyi returned unknown task status: ${status}`);
      }
      const urls = findUrls(result.results ?? result.result ?? result.output ?? result.data);
      if (urls.length === 0) throw new Error(`Haiyi task ${taskId} succeeded without a video URL`);
      const url = urls[0];
      if (url === undefined) throw new Error(`Haiyi task ${taskId} succeeded without a video URL`);
      return { status: "ready", receipt: { id: taskId }, handle: { taskId, url } };
    },
    async collect(context) {
      const handle = object(context.handle, "Haiyi result handle");
      const url = text(handle.url, "Haiyi result URL");
      await context.reportProgress?.({ phase: "Receiving generated video" });
      const response = await fetcher(url, { signal: AbortSignal.timeout(600_000) });
      if (!response.ok) throw new Error(`Haiyi video download returned HTTP ${response.status}`);
      const mediaType = response.headers.get("content-type")?.split(";")[0]?.trim()
        ?? (url.toLowerCase().endsWith(".mov") ? "video/quicktime" : "video/mp4");
      if (!mediaType.startsWith("video/")) throw new Error("Haiyi result is not video media");
      const artifact = await context.resources.put(new Uint8Array(await response.arrayBuffer()), mediaType);
      return {
        status: "completed",
        result: { value: { kind: "inline", value: canonicalize(sealGeneratedVideoSet({ videos: [artifact] })) } },
      };
    },
  };

  const imageEndpoint: AsyncEndpoint = {
    async start(context) {
      const authored = context.need.constraints as unknown as GenerationRequest;
      const support = imageSupport(context.need);
      if (support.status === "unsupported") throw new Error(support.reason);
      const wire = await compileWireRequest(imageMapping, authored, async (artifact) =>
        await upload(artifact, context.resources, context.credentials));
      const operation = authored.ports.images === undefined ? "text2image" : "image2image";
      await context.reportProgress?.({ phase: `Preparing Haiyi image request: ${operation}` });
      const submitted = await request("/openapi/v1/generate/image", context.credentials, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          model: { provider: "openai", model: "gpt-image-2.5-flare", type: operation },
          parameters: normalizeImageParameters(wire.input as Record<string, unknown>),
        }),
      });
      const taskId = findString(submitted, ["task_id", "taskId", "id"]);
      if (taskId === undefined) throw new Error("Haiyi image submission did not return task_id");
      const handle = { taskId, media: "image" };
      const receipt = { id: taskId };
      await context.checkpoint?.({ handle, receipt });
      return { ...wakeAfter(handle, interval), receipt };
    },
    async poll(context) {
      const taskId = text(object(context.handle, "Haiyi image handle").taskId, "Haiyi task id");
      const result = await request(`/openapi/v1/generate/result/${encodeURIComponent(taskId)}`, context.credentials);
      const status = text(result.status ?? nestedObject(result, "data")?.status, "Haiyi task status").toLowerCase();
      if (["pending", "queued", "running", "processing", "created"].includes(status)) {
        return wakeAfter({ taskId, media: "image" }, interval, Date.now(), { phase: status });
      }
      if (["fail", "failed", "error", "cancelled", "canceled"].includes(status)) {
        const failure = publicFailure(result) ?? { code: "HAIYI_TASK_FAILED", message: `Haiyi image task ${taskId} failed` };
        return { status: "failed", receipt: { id: taskId }, failure: { code: failure.code, message: failure.message } };
      }
      if (status !== "success" && status !== "succeeded" && status !== "completed" && status !== "ready") {
        throw new Error(`Haiyi returned unknown image task status: ${status}`);
      }
      const urls = findUrls(result.results ?? result.result ?? result.output ?? result.data);
      const url = urls[0];
      if (url === undefined) throw new Error(`Haiyi image task ${taskId} succeeded without an image URL`);
      return { status: "ready", receipt: { id: taskId }, handle: { taskId, media: "image", url } };
    },
    async collect(context) {
      const handle = object(context.handle, "Haiyi image result handle");
      const url = text(handle.url, "Haiyi image result URL");
      await context.reportProgress?.({ phase: "Receiving generated image" });
      const response = await fetcher(url, { signal: AbortSignal.timeout(300_000) });
      if (!response.ok) throw new Error(`Haiyi image download returned HTTP ${response.status}`);
      const mediaType = response.headers.get("content-type")?.split(";")[0]?.trim()
        ?? (url.toLowerCase().endsWith(".jpg") || url.toLowerCase().endsWith(".jpeg") ? "image/jpeg" : "image/png");
      if (!mediaType.startsWith("image/")) throw new Error("Haiyi result is not image media");
      const artifact = await context.resources.put(new Uint8Array(await response.arrayBuffer()), mediaType);
      return {
        status: "completed",
        result: { value: { kind: "inline", value: canonicalize(sealGeneratedImageSet({ images: [artifact] })) } },
      };
    },
  };

  const supports = (request: EndpointRequest) => serviceSupport(request);

  const endpointDefinition = defineEndpoint({
    instance: options.instance,
    pool: options.pool,
    credentials: { apiKey: options.apiKey },
    credentialInputs: { apiKey: { label: "Haiyi API token" } },
    defaultConcurrency: options.defaultConcurrency ?? 1,
    ...(options.actionLimits === undefined
      ? { actionLimits: { submit: { concurrency: 1 }, poll: { concurrency: 4 }, collect: { concurrency: 2 } } }
      : { actionLimits: options.actionLimits }),
    capabilities: [{
      capability,
      returns: generationTypes.videoSet,
      lifecycle: "asynchronous",
      supports,
      endpoint: videoEndpoint,
    }, {
      capability: imageCapability,
      returns: generationTypes.imageSet,
      lifecycle: "asynchronous",
      supports: imageSupport,
      endpoint: imageEndpoint,
    }],
    async readPricing(context) {
      const url = new URL("/openapi/v1/model/info", base);
      const image = context.request.capability.module.name === imageCapability.module.name;
      url.searchParams.set("provider", image ? "openai" : HAIYI_PROVIDER);
      url.searchParams.set("model", image ? "gpt-image-2.5-flare" : HAIYI_MODEL);
      const authored = context.request.constraints as unknown as GenerationRequest;
      url.searchParams.set("type", image
        ? authored.ports.images === undefined ? "text2image" : "image2image"
        : modeOf(authored));
      const credentials = await context.credentials();
      const info = await request(url.pathname + url.search, credentials);
      return [{
        source: url.href,
        data: canonicalize(info),
        summary: "海艺价格以当前模型信息中的实时参数规则为准",
      }];
    },
  });
  return endpointDefinition;
}

function serviceSupport(request: EndpointRequest) {
  if (request.capability.module.name !== capability.module.name
    || request.capability.module.version !== capability.module.version
    || request.capability.name !== capability.name) {
    return { status: "unsupported" as const, reason: "Haiyi Provider only serves Seedance 2.5" };
  }
  const ports = (request.constraints as unknown as GenerationRequest).ports;
  const duration = ports.duration?.[0];
  if (typeof duration !== "number" || duration < SUPPORTED_SECONDS.min || duration > SUPPORTED_SECONDS.max) {
    return { status: "unsupported" as const, reason: "Haiyi Seedance 2.5 supports 4–30 seconds for this Provider" };
  }
  const resolution = ports.resolution?.[0];
  if (resolution !== undefined && !SUPPORTED_RESOLUTIONS.has(String(resolution))) {
    return { status: "unsupported" as const, reason: "Haiyi Seedance 2.5 Provider supports 480p or 720p" };
  }
  return mappingSupportsRequest(mapping, request.constraints)
    ? { status: "supported" as const }
    : { status: "unsupported" as const, reason: "Haiyi does not accept one of the requested Seedance inputs" };
}

function imageSupport(request: EndpointRequest) {
  if (request.capability.module.name !== imageCapability.module.name
    || request.capability.module.version !== imageCapability.module.version
    || request.capability.name !== imageCapability.name) {
    return { status: "unsupported" as const, reason: "Haiyi Provider only serves GPT Image 2 through its gpt-image capability" };
  }
  const ports = (request.constraints as unknown as GenerationRequest).ports;
  const resolution = ports.resolution?.[0];
  if (resolution !== undefined && !["1K", "2K", "4K"].includes(String(resolution))) {
    return { status: "unsupported" as const, reason: "Haiyi GPT Image supports 1K, 2K or 4K" };
  }
  const ratio = ports.aspectRatio?.[0];
  if (ratio !== undefined && !["auto", "1:1", "3:2", "2:3", "2:1", "4:5", "5:4", "4:3", "3:4", "16:9", "9:16", "21:9"].includes(String(ratio))) {
    return { status: "unsupported" as const, reason: "Haiyi GPT Image does not support this aspect ratio" };
  }
  if ((ports.images?.length ?? 0) > 10) {
    return { status: "unsupported" as const, reason: "Haiyi GPT Image accepts at most 10 reference images" };
  }
  return mappingSupportsRequest(imageMapping, request.constraints)
    ? { status: "supported" as const }
    : { status: "unsupported" as const, reason: "Haiyi GPT Image does not accept one of the requested inputs" };
}
