import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {canonical,normalizeCommand,newSigningKey,newEncryptionKey,signCommand,verifyCommand,exportPublicKey,
  encryptPayload,decryptPayload,OfflineQueue} from '../src/index.js';

test('RFC8785 command encoding matches Python including Unicode ordering',()=>{
  const value={z:null,aa:[true,42],nested:{'😀':'tea','€':'\n'},s:'茶'};
  const result=spawnSync('../../apps/api/.venv/bin/python',['-c','import sys,json,rfc8785;sys.stdout.buffer.write(rfc8785.dumps(json.load(sys.stdin)))'],{input:JSON.stringify(value),encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);assert.equal(canonical(value),result.stdout);
  assert.throws(()=>canonical({x:NaN}));assert.throws(()=>canonical('\ud800'));
});
test('nonextractable Ed25519 keys sign commands and reject tampering',async()=>{
  const keys=await newSigningKey(), pub=await exportPublicKey(keys.publicKey);
  const signed=await signCommand({operation_id:crypto.randomUUID(),batch_id:'x'},keys.privateKey);
  assert.equal(await verifyCommand(signed,pub),true);
  signed.command.batch_id='y';assert.equal(await verifyCommand(signed,pub),false);
  await assert.rejects(crypto.subtle.exportKey('pkcs8',keys.privateKey));
});
test('AES-GCM binds ciphertext to deployment and batch context',async()=>{
  const key=await newEncryptionKey(), context={deployment:'local',batch:'a'};
  const envelope=await encryptPayload({quantity:42,recipe:[20,22]},key,crypto.randomUUID(),context);
  assert.deepEqual(await decryptPayload(envelope,key,context),{quantity:42,recipe:[20,22]});
  await assert.rejects(decryptPayload(envelope,key,{...context,batch:'b'}));
  assert.notEqual((await encryptPayload({},key,crypto.randomUUID(),context)).nonce,envelope.nonce);
});
function store(){ const rows=new Map();return {get:async id=>structuredClone(rows.get(id)),
  put:async row=>rows.set(row.id,structuredClone(row)),list:async()=>[...rows.values()].map(x=>structuredClone(x))}; }
test('offline timeout retains original signature and retry identity',async()=>{
  const db=store(), calls=[],signed={command:{operation_id:crypto.randomUUID()},signature:'unchanged'};
  let fail=true;
  const queue=new OfflineQueue(db,'http://localhost',async(url,options)=>{calls.push(options);
    if(fail)throw Error();return {ok:true,json:async()=>({status:'RECORDED'})};});
  await queue.enqueue('/v1/workflows',signed);await queue.sync('token',1000);
  assert.equal((await db.list())[0].status,'RETRY');fail=false;
  await queue.sync('new-token',10000);assert.equal((await db.list())[0].status,'RECORDED');
  assert.equal(calls[0].body,calls[1].body);
  assert.equal(calls[0].headers['Idempotency-Key'],calls[1].headers['Idempotency-Key']);
});
test('offline conflicts stop dependent submissions; altered operations cannot overwrite',async()=>{
  const db=store(),queue=new OfflineQueue(db,'',async()=>({ok:false,status:409}));
  const signed={command:{operation_id:crypto.randomUUID()},signature:'a'};
  await queue.enqueue('/v1/workflows',signed);
  await queue.enqueue('/v1/workflows',{command:{operation_id:crypto.randomUUID()},signature:'b'});
  await assert.rejects(queue.enqueue('/v1/workflows',{...signed,signature:'tampered'}));
  await queue.sync('token');assert.deepEqual((await db.list()).map(x=>x.status),['CONFLICT','QUEUED']);
});

test('a browser-signed normalized command verifies with the real Python schema',async()=>{
  const keys=await newSigningKey();
  const c=normalizeCommand({schema_version:'1.0',deployment_id:'test',actor_id:crypto.randomUUID(),
    org_id:crypto.randomUUID(),operation_id:crypto.randomUUID(),batch_id:crypto.randomUUID(),
    occurred_at:'2026-10-19T10:00:00.123+05:30',command_type:'CREATE_BATCH',external_id:'demo',
    public_alias:'DEMO-1234',material_class:'GREEN_LEAF',synthetic:true});
  const signed=await signCommand(c,keys.privateKey);
  const script=`import json,sys,base64
from teapass.schemas import CreateBatchCommand
from teapass.security import command_bytes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
v=json.load(sys.stdin)
c=CreateBatchCommand.model_validate(v['signed']['command'])
Ed25519PublicKey.from_public_bytes(base64.b64decode(v['public'])).verify(base64.b64decode(v['signed']['signature']),command_bytes(c))
print('verified')`;
  const result=spawnSync('../../apps/api/.venv/bin/python',['-c',script],{encoding:'utf8',
    env:{...process.env,PYTHONPATH:'../../apps/api'},input:JSON.stringify({signed,public:await exportPublicKey(keys.publicKey)})});
  assert.equal(result.status,0,result.stderr);assert.equal(result.stdout.trim(),'verified');
});

test('auditor receives a context-bound wrapped data key; wrong recipient and grant fail',async()=>{
  const {newShareableEncryptionKey,newRecipientKey,wrapDataKey,unwrapDataKey}=await import('../src/index.js');
  const dataKey=await newShareableEncryptionKey(), recipient=await newRecipientKey(), wrong=await newRecipientKey();
  const context={deployment:'local',batch:'batch-a',grant:'grant-a',recipient:'auditor-a'};
  const keyId=crypto.randomUUID();
  const payload=await encryptPayload({privateMeasurement:3},dataKey,keyId,{batch:'batch-a'});
  const wrapped=await wrapDataKey(dataKey,await exportPublicKey(recipient.publicKey),keyId,context);
  const key=await unwrapDataKey(wrapped,recipient,context);
  assert.deepEqual(await decryptPayload(payload,key,{batch:'batch-a'}),{privateMeasurement:3});
  await assert.rejects(unwrapDataKey(wrapped,wrong,context));
  await assert.rejects(unwrapDataKey(wrapped,recipient,{...context,grant:'grant-b'}));
  await assert.rejects(crypto.subtle.exportKey('raw',key));
});

test('public batch references match Python and are deployment-bound',async()=>{
  const {batchReference}=await import('../src/index.js');const batchId=crypto.randomUUID();
  const reference=await batchReference('teapass-local',batchId);
  const result=spawnSync('../../apps/api/.venv/bin/python',['-c',
    'import sys;from teapass.security import batch_reference;print(batch_reference("teapass-local",sys.argv[1]))',batchId],
    {encoding:'utf8',env:{...process.env,PYTHONPATH:'../../apps/api'}});
  assert.equal(result.status,0,result.stderr);assert.equal(result.stdout.trim(),reference);
  assert.notEqual(await batchReference('other',batchId),reference);
});
