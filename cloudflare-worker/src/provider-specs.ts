import providerManifest from "../../src/roco_serverchan_notifier/shared/provider_manifest.json";
import type { ProviderSpec } from "./types";

type ProviderManifestEntry = ProviderSpec & { type: string };
type ProviderManifest = {
  providers: ProviderManifestEntry[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function validateProviderManifest(value: unknown): ProviderManifest {
  if (!isRecord(value)) {
    throw new Error("Invalid provider manifest: root must be an object");
  }

  const providersValue = value.providers;
  if (!Array.isArray(providersValue)) {
    throw new Error("Invalid provider manifest: providers must be an array");
  }

  const providers: ProviderManifestEntry[] = [];
  const seenTypes = new Set<string>();

  providersValue.forEach((providerValue, providerIndex) => {
    if (!isRecord(providerValue)) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}] must be an object`);
    }

    const { type, label, description, envId, envVars, fields } = providerValue;
    if (typeof type !== "string" || !type.trim()) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].type must be a non-empty string`);
    }
    if (seenTypes.has(type)) {
      throw new Error(`Invalid provider manifest: duplicate provider type ${type}`);
    }
    seenTypes.add(type);

    if (typeof label !== "string" || !label.trim()) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].label must be a non-empty string`);
    }
    if (typeof description !== "string" || !description.trim()) {
      throw new Error(
        `Invalid provider manifest: providers[${providerIndex}].description must be a non-empty string`
      );
    }
    if (typeof envId !== "string" || !envId.trim()) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].envId must be a non-empty string`);
    }
    if (!isRecord(envVars)) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].envVars must be an object`);
    }
    if (!Array.isArray(fields)) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].fields must be an array`);
    }

    const fieldNames = new Set<string>();
    const normalizedFields = fields.map((fieldValue, fieldIndex) => {
      if (!isRecord(fieldValue)) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}] must be an object`
        );
      }

      const { name, label, secret, required, default: defaultValue } = fieldValue;
      if (typeof name !== "string" || !name.trim()) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].name must be a non-empty string`
        );
      }
      if (typeof label !== "string" || !label.trim()) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].label must be a non-empty string`
        );
      }
      if (fieldNames.has(name)) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}] contains duplicate field ${name}`
        );
      }
      fieldNames.add(name);
      if (secret !== undefined && typeof secret !== "boolean") {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].secret must be a boolean`
        );
      }
      if (required !== undefined && typeof required !== "boolean") {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].required must be a boolean`
        );
      }
      if (defaultValue !== undefined && typeof defaultValue !== "string") {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].default must be a string`
        );
      }

      return {
        name,
        label,
        ...(secret !== undefined ? { secret } : {}),
        ...(required !== undefined ? { required } : {}),
        ...(defaultValue !== undefined ? { default: defaultValue } : {}),
      };
    });

    const normalizedEnvVars: Record<string, string> = {};
    for (const [envName, envValue] of Object.entries(envVars)) {
      if (typeof envName !== "string" || !envName.trim()) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].envVars contains an empty key`
        );
      }
      if (typeof envValue !== "string" || !envValue.trim()) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].envVars.${envName} must be a non-empty string`
        );
      }
      if (!fieldNames.has(envName)) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].envVars.${envName} is not declared in fields`
        );
      }
      normalizedEnvVars[envName] = envValue;
    }

    providers.push({
      type,
      label,
      description,
      envId,
      envVars: normalizedEnvVars,
      fields: normalizedFields,
    });
  });

  return { providers };
}

const manifest = validateProviderManifest(providerManifest);

export const PROVIDER_TYPES: Record<string, ProviderSpec> = Object.fromEntries(
  manifest.providers.map(({ type, ...spec }) => [type, spec])
) as Record<string, ProviderSpec>;

export function providerSpec(providerType: string): ProviderSpec | undefined {
  return PROVIDER_TYPES[providerType];
}

export function providerSecretFields(providerType: string): Set<string> {
  const spec = providerSpec(providerType);
  if (!spec) return new Set();
  return new Set(
    spec.fields.filter((f) => f.secret).map((f) => f.name)
  );
}

export function providerRequiredFields(providerType: string): Set<string> {
  const spec = providerSpec(providerType);
  if (!spec) return new Set();
  return new Set(
    spec.fields.filter((f) => f.required).map((f) => f.name)
  );
}

export function providerFieldDefault(
  providerType: string,
  fieldName: string
): string | undefined {
  const spec = providerSpec(providerType);
  const field = spec?.fields.find((item) => item.name === fieldName);
  return field && Object.prototype.hasOwnProperty.call(field, "default")
    ? field.default
    : undefined;
}

export function providerEnvFields(providerType: string): Record<string, string> {
  const spec = providerSpec(providerType);
  if (!spec) return {};
  return { ...spec.envVars };
}

export function providerEnvBindingNames(): string[] {
  return [
    ...new Set(
      Object.values(PROVIDER_TYPES).flatMap((spec) => Object.values(spec.envVars))
    ),
  ];
}

export function providerEnvId(providerType: string): string {
  const spec = providerSpec(providerType);
  return spec?.envId || `${providerType}-env`;
}
