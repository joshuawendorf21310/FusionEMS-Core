# INTEGRATIONS

## Integration Registry
- Registry is tenant-scoped (`integration_registry` table) and keyed by `(tenant_id, provider_name)`.
- Supported providers: STRIPE, TELNYX, WEATHER, REDIS, SES, OPENAI, OTHER.
- Config is accepted as plaintext JSON at API boundary, then encrypted before persistence.
- Stored fields: ciphertext, encrypted data key, nonce, key id, encryption context.
- Config payload is never returned by API responses.
- Enable/disable emits integration events post-commit.


## Redis realtime
- Redis publisher emits JSON events to channel `events`.
- WebSocket subscriptions are tenant-scoped; channel tenant must match JWT tenant.
- Redis connection can be configured via `redis_url`.
