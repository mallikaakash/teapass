/** Browser/Node WebCrypto helpers. Private keys are nonextractable; no server key custody. */
const encoder = new TextEncoder();
export function canonical(value) {
  if (value === null || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'string') {
    if (/[\uD800-\uDFFF]/u.test(value)) throw new TypeError('Unpaired Unicode surrogate');
    return JSON.stringify(value);
  }
  if (typeof value === 'number') {
    if (!Number.isSafeInteger(value)) throw new TypeError('Only safe integer command numbers are supported');
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype)
    return '{' + Object.keys(value).sort().map(k => canonical(k) + ':' + canonical(value[k])).join(',') + '}';
  throw new TypeError('Only JSON values are supported');
}
export const toBase64 = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes)));
export const fromBase64 = text => Uint8Array.from(atob(text), c => c.charCodeAt(0));
export const newSigningKey = () => crypto.subtle.generateKey('Ed25519', false, ['sign','verify']);
export const newEncryptionKey = () => crypto.subtle.generateKey({name:'AES-GCM',length:256}, false, ['encrypt','decrypt']);
export const exportPublicKey = async key => toBase64(await crypto.subtle.exportKey('raw', key));
export const commandBytes = command => encoder.encode('TEAPASS_OPERATION_V1\0' + canonical(command));
/** Match the API's normalized optional fields and UTC timestamp encoding before signing. */
export function normalizeCommand(input) {
  const c=structuredClone(input);
  c.encrypted_payload ??= null;
  if(c.command_type==='CREATE_BATCH') c.published ??= false;
  if(c.command_type==='APPEND_EVENT') c.supersedes_event_id ??= null;
  if(c.command_type==='OFFER_CUSTODY') c.inventory_tx_id ??= null;
  if(c.command_type==='PREPARE_CHAIN') c.input_batch_ids ??= [];
  // JS Date has millisecond precision; callers needing microseconds must pass normalized UTC text.
  const format=value=>{
    if(typeof value==='string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(value)) return value;
    const iso=new Date(value).toISOString();
    return iso.endsWith('.000Z') ? iso.slice(0,-5)+'Z' : iso.slice(0,-1)+'000Z';
  };
  c.occurred_at=format(c.occurred_at);
  // Expiry fields are not normalized by the API; use UTC to obtain a stable representation.
  if(c.expires_at) c.expires_at=format(c.expires_at);
  for(const name of ['actor_id','org_id','operation_id','batch_id','transfer_id','receiver_id',
    'grant_id','recipient_id','attestation_id','job_id','supersedes_event_id'])
    if(c[name]) c[name]=c[name].toLowerCase();
  if(c.input_batch_ids) c.input_batch_ids=c.input_batch_ids.map(id=>id.toLowerCase());
  if(c.encrypted_payload) c.encrypted_payload.key_id=c.encrypted_payload.key_id.toLowerCase();
  if(c.key_envelope) c.key_envelope.key_id=c.key_envelope.key_id.toLowerCase();
  return c;
}
export async function signCommand(command, privateKey) {
  return {command:structuredClone(command),signature:toBase64(await crypto.subtle.sign('Ed25519', privateKey, commandBytes(command)))};
}
export async function verifyCommand(signed, publicKeyBase64) {
  const key=await crypto.subtle.importKey('raw',fromBase64(publicKeyBase64),'Ed25519',false,['verify']);
  return crypto.subtle.verify('Ed25519',key,fromBase64(signed.signature),commandBytes(signed.command));
}
/** Caller binds batch, deployment and intended recipient in context; the same context is needed to decrypt. */
export async function encryptPayload(value, key, keyId, context) {
  const nonce=crypto.getRandomValues(new Uint8Array(12));
  const ciphertext=await crypto.subtle.encrypt({name:'AES-GCM',iv:nonce,
    additionalData:encoder.encode('TEAPASS_ENVELOPE_V1\0'+canonical(context))},key,encoder.encode(canonical(value)));
  if(ciphertext.byteLength>65536) throw new RangeError('Encrypted payload exceeds 64 KiB');
  return {algorithm:'A256GCM',key_id:keyId,nonce:toBase64(nonce),ciphertext:toBase64(ciphertext)};
}
export async function decryptPayload(envelope, key, context) {
  if(envelope.algorithm!=='A256GCM') throw new TypeError('Unsupported encryption');
  const plaintext=await crypto.subtle.decrypt({name:'AES-GCM',iv:fromBase64(envelope.nonce),
    additionalData:encoder.encode('TEAPASS_ENVELOPE_V1\0'+canonical(context))},key,fromBase64(envelope.ciphertext));
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(plaintext));
}

/** Durable signed queue. Conflicts require explicit user resolution and a new signed operation. */
export class OfflineQueue {
  constructor(store, baseUrl, fetcher=fetch) { this.store=store; this.baseUrl=baseUrl; this.fetcher=fetcher; }
  async enqueue(path, signed) {
    if(!/^\/v1\/(batches(?:\/[a-f0-9-]{36}\/events)?|workflows)$/.test(path)) throw new TypeError('Unsupported command route');
    const id=signed.command.operation_id;
    const previous=await this.store.get(id);
    const row={id,path,signed:structuredClone(signed),idempotencyKey:id,status:'QUEUED',attempts:0,nextAttempt:0};
    if(previous && (canonical(previous.signed)!==canonical(signed) || previous.path!==path))
      throw new Error('Operation ID already belongs to a different signed command');
    if(!previous) await this.store.put(row);
    return id;
  }
  async sync(accessToken, now=Date.now()) {
    // Store iteration must preserve enqueue order so dependent event heads are submitted in order.
    for(const row of await this.store.list()) {
      if(['CONFLICT','REJECTED'].includes(row.status)) return;
      if(row.status==='RECORDED') continue;
      if(row.nextAttempt>now) return;
      try {
        const response=await this.fetcher(this.baseUrl+row.path,{method:'POST',
          headers:{'Content-Type':'application/json',Authorization:'Bearer '+accessToken,'Idempotency-Key':row.idempotencyKey},
          body:JSON.stringify(row.signed),signal:AbortSignal.timeout(15000)});
        if(response.ok) { row.status='RECORDED'; row.result=await response.json(); }
        else if(response.status===401) return; // refresh login, retaining all commands
        else if(response.status===409) row.status='CONFLICT';
        else if(response.status===403 || response.status===422 || response.status===404) row.status='REJECTED';
        else throw new Error('Retryable dependency failure');
      } catch {
        row.status='RETRY';row.attempts++;
        row.nextAttempt=now+Math.min(300000,1000*2**Math.min(row.attempts,8));
      }
      await this.store.put(row);
      if(row.status!=='RECORDED') return; // do not submit dependent stale heads
    }
  }
}
export async function openBrowserStore(name='teapass-signed-queue-v1') {
  const db=await new Promise((resolve,reject)=>{
    const req=indexedDB.open(name,1);
    req.onupgradeneeded=()=>{ req.result.createObjectStore('commands',{keyPath:'id'}); };
    req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);
  });
  const transaction=(mode,fn)=>new Promise((resolve,reject)=>{
    const tx=db.transaction('commands',mode), request=fn(tx.objectStore('commands'));
    tx.oncomplete=()=>resolve(request.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);
  });
  return {
    get:id=>transaction('readonly',s=>s.get(id)),
    put:async row=>{ const old=await transaction('readonly',s=>s.get(row.id));
      return transaction('readwrite',s=>s.put({...row,enqueuedAt:old?.enqueuedAt ?? Date.now()})); },
    list:async()=> (await transaction('readonly',s=>s.getAll())).sort((a,b)=>a.enqueuedAt-b.enqueuedAt),
    close:()=>db.close(),
  };
}

/** Opt-in shareable data keys can be wrapped for a named recipient. Never upload/export them unwrapped. */
export const newShareableEncryptionKey = () => crypto.subtle.generateKey({name:'AES-GCM',length:256}, true, ['encrypt','decrypt']);
export const newRecipientKey = () => crypto.subtle.generateKey('X25519', false, ['deriveBits']);
async function wrappingKey(privateKey, publicKey, context) {
  const bits=await crypto.subtle.deriveBits({name:'X25519',public:publicKey},privateKey,256);
  try {
    const hkdf=await crypto.subtle.importKey('raw',bits,'HKDF',false,['deriveKey']);
    return await crypto.subtle.deriveKey({name:'HKDF',hash:'SHA-256',
      salt:await crypto.subtle.digest('SHA-256',encoder.encode(canonical(context))),
      info:encoder.encode('TEAPASS_RECIPIENT_KEY_V1')},hkdf,{name:'AES-GCM',length:256},false,['wrapKey','unwrapKey']);
  } finally {new Uint8Array(bits).fill(0);}
}
export async function wrapDataKey(dataKey, recipientPublicBase64, keyId, context) {
  const recipient=await crypto.subtle.importKey('raw',fromBase64(recipientPublicBase64),'X25519',false,[]);
  const ephemeral=await newRecipientKey();
  const ephemeral_public_key=await exportPublicKey(ephemeral.publicKey);
  const wrapping=await wrappingKey(ephemeral.privateKey,recipient,context);
  const nonce=crypto.getRandomValues(new Uint8Array(12));
  const aad=encoder.encode(canonical({domain:'TEAPASS_KEY_ENVELOPE_V1',keyId,context,
    ephemeral_public_key,recipient:recipientPublicBase64}));
  const wrapped=await crypto.subtle.wrapKey('raw',dataKey,wrapping,{name:'AES-GCM',iv:nonce,additionalData:aad});
  return {algorithm:'X25519-HKDF-SHA256-A256GCM',key_id:keyId,ephemeral_public_key,
    nonce:toBase64(nonce),ciphertext:toBase64(wrapped)};
}
export async function unwrapDataKey(envelope, recipientKeys, context) {
  if(envelope.algorithm!=='X25519-HKDF-SHA256-A256GCM') throw new TypeError('Unsupported key wrapping');
  const ephemeral=await crypto.subtle.importKey('raw',fromBase64(envelope.ephemeral_public_key),'X25519',false,[]);
  const wrapping=await wrappingKey(recipientKeys.privateKey,ephemeral,context);
  const aad=encoder.encode(canonical({domain:'TEAPASS_KEY_ENVELOPE_V1',keyId:envelope.key_id,context,
    ephemeral_public_key:envelope.ephemeral_public_key,recipient:await exportPublicKey(recipientKeys.publicKey)}));
  return crypto.subtle.unwrapKey('raw',fromBase64(envelope.ciphertext),wrapping,
    {name:'AES-GCM',iv:fromBase64(envelope.nonce),additionalData:aad},{name:'AES-GCM'},false,['decrypt']);
}

/** Public commitment metadata binds an operational batch to this deployment without publishing its quantity. */
export async function batchReference(deploymentId,batchId) {
  if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(batchId)) throw new TypeError('Normalized UUID required');
  const digest=await crypto.subtle.digest('SHA-256',encoder.encode('TEAPASS_BATCH_V1\0'+deploymentId+'\0'+batchId));
  return [...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
