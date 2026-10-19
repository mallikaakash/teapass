/** Read-only sidecar. Bind loopback; the FastAPI public endpoint supplies rate/body boundaries. */
import { createServer } from 'node:http';
import { WebSocket } from 'ws';
import { verifyClaim, bytes32, type VerifierConfig } from './claim-verifier.js';
Object.defineProperty(globalThis,'WebSocket',{value:WebSocket,configurable:true});
const config:VerifierConfig={contractAddress:process.env.TEAPASS_MIDNIGHT_CONTRACT_ADDRESS??'',
  network:process.env.TEAPASS_MIDNIGHT_NETWORK??'undeployed',
  indexer:process.env.TEAPASS_MIDNIGHT_INDEXER_URL??'http://127.0.0.1:8088/api/v4/graphql',
  indexerWS:process.env.TEAPASS_MIDNIGHT_INDEXER_WS??'ws://127.0.0.1:8088/api/v4/graphql/ws',
  node:process.env.TEAPASS_MIDNIGHT_NODE_URL??'http://127.0.0.1:9944'};
bytes32(config.contractAddress);
let active=0;
const server=createServer(async(req,res)=>{
  res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');
  const match=/^\/claims\/([a-f0-9]{64})$/.exec(req.url??'');
  if(req.method!=='GET' || !match){res.writeHead(404).end('{}');return;}
  if(active>=4){res.writeHead(503).end('{"error":"VERIFIER_BUSY"}');return;}
  active++;
  try {const claim=await verifyClaim(config,match[1]);res.writeHead(claim?200:404).end(JSON.stringify(claim??{error:'CLAIM_NOT_FOUND'}));}
  catch {res.writeHead(503).end('{"error":"CHAIN_VERIFICATION_UNAVAILABLE"}');}
  finally {active--;}
});
server.requestTimeout=10000;server.headersTimeout=10000;
server.listen(6301,'127.0.0.1',()=>process.stdout.write('TeaPass read-only verifier on 127.0.0.1:6301\n'));
for(const signal of ['SIGINT','SIGTERM']) process.on(signal,()=>server.close(()=>process.exit(0)));
