import {
  createRuntimeEndpointAdapterFacet,
  runtimeConfigActionLimits,
  runtimeConfigCredentialRef,
  runtimeConfigExact,
  runtimeConfigObject,
  runtimeConfigPositiveInteger,
  runtimeConfigString,
} from "@hypit/runtime-local/extension";

import { createHaiyiProvider, providerModule } from "./provider.js";

export default {
  format: "hypit.package@1" as const,
  facets: [createRuntimeEndpointAdapterFacet({
    use: providerModule.name,
    activate(context) {
      const config = runtimeConfigObject(context.config, "Haiyi");
      runtimeConfigExact(config, [
        "baseUrl",
        "apiKey",
        "defaultConcurrency",
        "actionLimits",
        "pollIntervalMs",
        "requestTimeoutMs",
      ], "Haiyi");
      if (context.pool === undefined) throw new Error("Haiyi Provider Pool is required");
      const baseUrl = runtimeConfigString(config.baseUrl, "Haiyi baseUrl");
      const apiKey = runtimeConfigCredentialRef(config.apiKey, "Haiyi apiKey");
      if (apiKey === undefined) throw new Error("Haiyi apiKey CredentialRef is required");
      const defaultConcurrency = runtimeConfigPositiveInteger(config.defaultConcurrency, "Haiyi defaultConcurrency");
      const pollIntervalMs = runtimeConfigPositiveInteger(config.pollIntervalMs, "Haiyi pollIntervalMs");
      const requestTimeoutMs = runtimeConfigPositiveInteger(config.requestTimeoutMs, "Haiyi requestTimeoutMs");
      const actionLimits = runtimeConfigActionLimits(config.actionLimits);
      return {
        endpoint: createHaiyiProvider({
          instance: context.instance,
          pool: context.pool,
          ...(baseUrl === undefined ? {} : { baseUrl }),
          apiKey,
          ...(defaultConcurrency === undefined ? {} : { defaultConcurrency }),
          ...(pollIntervalMs === undefined ? {} : { pollIntervalMs }),
          ...(requestTimeoutMs === undefined ? {} : { requestTimeoutMs }),
          ...(actionLimits === undefined ? {} : { actionLimits }),
        }),
      };
    },
  })],
};
