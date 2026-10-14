import assert from "node:assert/strict";
import test from "node:test";
import { EndpointRegistry, MemoryResourceStore } from "@hypit/executor";
import { generationTypes, assertMappingCoversPorts } from "@hypit/generation";
import { canonicalize } from "@hypit/hypit/endpoint";
import type { EndpointStartContext } from "@hypit/hypit/endpoint";
import { sealGptImage2Request, gptImage2Ports } from "@hypit/gpt-image";
import { sealSeedanceRequest, seedancePorts } from "@hypit/seedance";

import { capability, createHaiyiProvider, imageCapability, imageMapping, mapping } from "../src/provider.js";

test("Haiyi mapping covers every Seedance 2.5 port", () => {
  assertMappingCoversPorts(seedancePorts["seedance-2.5"], mapping);
  assertMappingCoversPorts(gptImage2Ports, imageMapping);
});

test("Haiyi Provider serves GPT Image text-to-image", async () => {
  const provider = createHaiyiProvider({
    instance: "haiyi.default", pool: "haiyi.default", baseUrl: "https://art.huya.info",
    apiKey: { store: "env", key: "HAIYI_API_TOKEN" }, pollIntervalMs: 0,
    fetch: async (input, init) => {
      const url = new URL(String(input));
      if (url.pathname === "/openapi/v1/generate/image") {
        assert.deepEqual(JSON.parse(String(init?.body)), {
          model: { provider: "openai", model: "gpt-image-2.5-flare", type: "text2image" },
          parameters: { prompt: "A blue glass orb", aspectRatio: "1:1", resolution: "2k" },
        });
        return Response.json({ task_id: "image-job" });
      }
      if (url.pathname === "/openapi/v1/generate/result/image-job") {
        return Response.json({ status: "success", results: [{ url: "https://cdn.example/image.png" }] });
      }
      if (url.hostname === "cdn.example") {
        return new Response(new Uint8Array([4, 5]), { headers: { "content-type": "image/png" } });
      }
      throw new Error(`Unexpected Haiyi image path ${url.pathname}`);
    },
  });
  const constraints = canonicalize(sealGptImage2Request({
    prompt: ["A blue glass orb"], aspectRatio: ["1:1"], resolution: ["2K"],
  }));
  const need = {
    id: "need:haiyi-image", capability: imageCapability, returns: generationTypes.imageSet,
    constraints, result: "record:haiyi-image",
  } as const;
  const resources = new MemoryResourceStore();
  const context: EndpointStartContext = {
    need, command: { kind: "fulfill-need", id: "command:haiyi-image", need }, operation: "operation:haiyi-image",
    resources, credentials: { apiKey: { secret: "test-token" } },
  };
  const registry = new EndpointRegistry(); await provider.install(registry);
  const resolved = registry.resolve(need);
  assert.equal(resolved.status, "resolved");
  if (resolved.status !== "resolved") return;
  assert.equal(resolved.registration.kind, "asynchronous");
  if (resolved.registration.kind !== "asynchronous") return;
  const started = await resolved.registration.endpoint.start(context);
  assert.equal(started.status, "pending");
  if (started.status !== "pending") return;
  const ready = await resolved.registration.endpoint.poll({ ...context, handle: started.handle });
  assert.equal(ready.status, "ready");
  if (ready.status !== "ready") return;
  const collected = await resolved.registration.endpoint.collect!({ ...context, handle: ready.handle });
  assert.equal(collected.status, "completed");
});

test("Haiyi Provider submits, polls and collects a text-to-video task", async () => {
  const calls: string[] = [];
  const provider = createHaiyiProvider({
    instance: "haiyi.default",
    pool: "haiyi.default",
    baseUrl: "https://art.huya.info",
    apiKey: { store: "env", key: "HAIYI_API_TOKEN" },
    pollIntervalMs: 0,
    fetch: async (input, init) => {
      const url = new URL(String(input));
      calls.push(url.pathname);
      if (url.pathname === "/openapi/v1/generate/video") {
        const body = JSON.parse(String(init?.body));
        assert.deepEqual(body, {
          model: { provider: "volcengine", model: "doubao-seedance-2-5-260628", type: "text2video" },
          parameters: {
            prompt: "A slow push-in",
            duration: 4,
            resolution: "720p",
            aspectRatio: "9:16",
            generateAudio: true,
            nsfw: false,
            output_format: "mp4",
            isUploadAsset: false,
          },
        });
        return Response.json({ task_id: "job-one" });
      }
      if (url.pathname === "/openapi/v1/generate/result/job-one") {
        return Response.json({ status: "success", results: [{ url: "https://cdn.example/video.mp4" }] });
      }
      if (url.hostname === "cdn.example") {
        return new Response(new Uint8Array([1, 2, 3]), { headers: { "content-type": "video/mp4" } });
      }
      throw new Error(`Unexpected Haiyi path ${url.pathname}`);
    },
  });
  const constraints = canonicalize(sealSeedanceRequest("seedance-2.5", {
    prompt: ["A slow push-in"],
    duration: [4],
    resolution: ["720p"],
    aspectRatio: ["9:16"],
    generateAudio: [true],
    webSearch: [false],
  }));
  const need = {
    id: "need:haiyi",
    capability,
    returns: generationTypes.videoSet,
    constraints,
    result: "record:haiyi",
  } as const;
  const resources = new MemoryResourceStore();
  const context: EndpointStartContext = {
    need,
    command: { kind: "fulfill-need", id: "command:haiyi", need },
    operation: "operation:haiyi",
    resources,
    credentials: { apiKey: { secret: "test-token" } },
  };
  const registry = new EndpointRegistry();
  await provider.install(registry);
  const resolved = registry.resolve(need);
  assert.equal(resolved.status, "resolved");
  if (resolved.status !== "resolved") return;
  assert.equal(resolved.registration.kind, "asynchronous");
  if (resolved.registration.kind !== "asynchronous") return;
  const started = await resolved.registration.endpoint.start(context);
  assert.equal(started.status, "pending");
  if (started.status !== "pending") return;
  const ready = await resolved.registration.endpoint.poll({ ...context, handle: started.handle });
  assert.equal(ready.status, "ready");
  if (ready.status !== "ready") return;
  const collected = await resolved.registration.endpoint.collect!({ ...context, handle: ready.handle });
  assert.equal(collected.status, "completed");
  assert.deepEqual(calls, [
    "/openapi/v1/generate/video",
    "/openapi/v1/generate/result/job-one",
    "/video.mp4",
  ]);
});

test("Frame inputs upload in order and use image2video for both submission and pricing", async () => {
  const resources = new MemoryResourceStore();
  const first = await resources.put(new Uint8Array([1, 2]), "image/png");
  const last = await resources.put(new Uint8Array([3, 4]), "image/png");
  let uploads = 0;
  const provider = createHaiyiProvider({
    instance: "haiyi.default", pool: "haiyi.default",
    apiKey: { store: "env", key: "HAIYI_API_TOKEN" },
    fetch: async (input, init) => {
      const url = new URL(String(input));
      if (url.pathname === "/openapi/v1/file/upload") {
        const file = (init?.body as FormData).get("file") as Blob;
        assert.deepEqual(new Uint8Array(await file.arrayBuffer()), uploads === 0 ? new Uint8Array([1, 2]) : new Uint8Array([3, 4]));
        uploads++;
        return Response.json({ url: `https://cdn.example/frame-${uploads}.png` });
      }
      if (url.pathname === "/openapi/v1/generate/video") {
        const body = JSON.parse(String(init?.body));
        assert.equal(body.model.type, "image2video");
        assert.equal(body.parameters.roleMode, "frame");
        assert.deepEqual(body.parameters.images, ["https://cdn.example/frame-1.png", "https://cdn.example/frame-2.png"]);
        assert.equal(body.parameters.isUploadAsset, true);
        return Response.json({ task_id: "frame-job" });
      }
      if (url.pathname === "/openapi/v1/model/info") {
        assert.equal(url.searchParams.get("type"), "image2video");
        return Response.json({ price: 1, unit: "test-only" });
      }
      throw new Error(`Unexpected path ${url.pathname}`);
    },
  });
  const constraints = canonicalize(sealSeedanceRequest("seedance-2.5", {
    prompt: ["Move from the first to the final pose"], duration: [4], resolution: ["720p"],
    aspectRatio: ["9:16"], generateAudio: [false], webSearch: [false],
    firstFrame: [{ role: "image", artifact: first, fields: { personReference: true } }],
    lastFrame: [{ role: "image", artifact: last, fields: { personReference: false } }],
  }));
  const need = { id: "need:frames", capability, returns: generationTypes.videoSet, constraints, result: "record:frames" } as const;
  const context: EndpointStartContext = {
    need, command: { kind: "fulfill-need", id: "command:frames", need }, operation: "operation:frames",
    resources, credentials: { apiKey: { secret: "test-token" } },
  };
  const registry = new EndpointRegistry(); await provider.install(registry);
  const resolved = registry.resolve(need);
  assert.equal(resolved.status, "resolved");
  if (resolved.status !== "resolved" || resolved.registration.kind !== "asynchronous") throw new Error("Frame request was not routed");
  assert.equal((await resolved.registration.endpoint.start(context)).status, "pending");
  assert.equal(uploads, 2);
  assert.ok(provider.readPricing);
  const prices = await provider.readPricing({ request: need, credentials: async () => context.credentials });
  assert.equal(prices.length, 1);
});
