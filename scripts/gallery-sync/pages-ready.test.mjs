import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { waitForPages, checkoutInputs, readOnlyClients, PagesReadyError, FILES, BUDGET_MS } from './pages-ready.mjs';
const A='a'.repeat(40), B='b'.repeat(40);
const receipt=(status='built',commit=A)=>({commit,status,updated_at:'2026-10-23T00:00:00Z'});
const expected={csv:Buffer.from('new CSV'),source:Buffer.from('{"new":"marker"}'),html:Buffer.from('new root HTML')};
function fixture(overrides={}) {
  const state={clock:0,buildCalls:0,mainCalls:0,productionCalls:[],sleeps:[],reports:[]};
  const config={revision:A,dataReleaseRevision:A,expected,budgetMs:100,intervalMs:10,maxAttempts:10,
    now:()=>state.clock,sleep:async ms=>{state.sleeps.push(ms);state.clock+=ms;},
    readMain:async()=>{state.mainCalls++;return A;},
    readBuilds:async()=>{state.buildCalls++;return [receipt()];},
    readProduction:async({key})=>{state.productionCalls.push(key);const body=config.expected[key];return {status:body===null?404:200,body};},
    onProgress:r=>state.reports.push(r),...overrides};
  return {state,config};
}
// Model the workflow's fail-closed sequencing; never calls the real D1 entry point.
async function modeledRun(config) {
  let syncInvocations=0;
  try {const result=await waitForPages(config);if(result.status==='READY')syncInvocations++;return {result,syncInvocations};}
  catch(error){return {error:error.code,syncInvocations};}
}
function blocked(result,code){assert.equal(result.error,code);assert.equal(result.syncInvocations,0);}

test('built exact revision + all three published bytes + stable main allows one sync',async()=>{
  const f=fixture(),r=await modeledRun(f.config);assert.equal(r.syncInvocations,1);assert.equal(r.result.receipt.commit,A);
  assert.deepEqual(f.state.productionCalls,['csv','source','html']);assert.ok(f.state.mainCalls>=6);
});
test('building -> built polls; never reads unpublished input or invokes sync while building',async()=>{
  const f=fixture();f.config.readBuilds=async()=>[receipt(++f.state.buildCalls===1?'building':'built')];
  const r=await modeledRun(f.config);assert.equal(r.syncInvocations,1);assert.equal(f.state.buildCalls,2);assert.equal(f.state.productionCalls.length,3);assert.deepEqual(f.state.sleeps,[10]);
});
for(const key of ['csv','source','html'])test(`${key} change waits for actual Production bytes, not main alone`,async()=>{
  const f=fixture();f.config.readBuilds=async()=>{f.state.buildCalls++;return [receipt()];};
  f.config.readProduction=async({key:k})=>({status:200,body:k===key&&f.state.buildCalls===1?Buffer.from('stale'):expected[k]});
  const r=await modeledRun(f.config);assert.equal(r.syncInvocations,1);assert.equal(f.state.buildCalls,2);
  assert.equal(f.state.reports[0].attempts[0].inputs[key].matches,false);
});
test('CSV, marker and HTML becoming visible separately must all match in one pass',async()=>{
  const f=fixture();f.config.readBuilds=async()=>{f.state.buildCalls++;return [receipt()];};
  f.config.readProduction=async({key})=>({status:200,body:f.state.buildCalls<({csv:2,source:3,html:4}[key])?Buffer.from('previous deployment'):expected[key]});
  const r=await modeledRun(f.config);assert.equal(r.syncInvocations,1);assert.equal(f.state.buildCalls,4);
});
test('legacy missing marker requires a real 404; stale present marker must disappear first',async()=>{
  const f=fixture({expected:{...expected,source:null}});f.config.readBuilds=async()=>{f.state.buildCalls++;return [receipt()];};
  f.config.readProduction=async({key})=>key==='source'?{status:f.state.buildCalls===1?200:404,body:Buffer.from('stale marker')}:{status:200,body:expected[key]};
  assert.equal((await modeledRun(f.config)).syncInvocations,1);assert.equal(f.state.buildCalls,2);
});
test('modern expected marker missing never passes',async()=>{
  const f=fixture({maxAttempts:2});f.config.readProduction=async({key})=>({status:key==='source'?404:200,body:expected[key]});
  blocked(await modeledRun(f.config),'PAGES_READY_ATTEMPTS_EXHAUSTED');
});
for(const status of ['errored','failed','cancelled'])test(`Pages ${status}: zero D1/sync invocations`,async()=>{
  const f=fixture({readBuilds:async()=>[receipt(status)]});blocked(await modeledRun(f.config),'PAGES_BUILD_FAILED');assert.equal(f.state.productionCalls.length,0);
});
test('newest failed build for same SHA does not fall back to an older built receipt',async()=>{
  blocked(await modeledRun(fixture({readBuilds:async()=>[receipt('errored'),receipt()]}).config),'PAGES_BUILD_FAILED');
});
test('other SHA built is not evidence for expected revision; missing receipt stops at cap',async()=>{
  const f=fixture({maxAttempts:2,readBuilds:async()=>[receipt('built',B)]});blocked(await modeledRun(f.config),'PAGES_READY_ATTEMPTS_EXHAUSTED');assert.equal(f.state.productionCalls.length,0);
});
test('deadline exhaustion while building: zero sync invocations',async()=>{
  const f=fixture({budgetMs:25,maxAttempts:99,readBuilds:async()=>[receipt('building')]});blocked(await modeledRun(f.config),'PAGES_READY_TIMEOUT');assert.equal(f.state.clock,25);
});
test('slow reads share the same deadline instead of resetting the budget',async()=>{
  const f=fixture({budgetMs:25});f.config.readBuilds=async()=>{f.state.clock+=26;return [receipt()];};blocked(await modeledRun(f.config),'PAGES_READY_TIMEOUT');
});
test('main changes during waiting: stop before another build or any sync',async()=>{
  const f=fixture({readBuilds:async()=>[receipt('building')]});f.config.readMain=async()=>f.state.sleeps.length?B:A;
  blocked(await modeledRun(f.config),'MAIN_CHANGED');assert.equal(f.state.sleeps.length,1);
});
test('main changes after published input checks, including final check: stop',async()=>{
  for(const at of [3,4,5,6]){const f=fixture();f.config.readMain=async()=>++f.state.mainCalls>=at?B:A;blocked(await modeledRun(f.config),'MAIN_CHANGED');}
});
test('unverifiable main fails closed without disclosing underlying credentials',async()=>{
  const f=fixture({readMain:async()=>{throw Error('sensitive simulated credential');}});blocked(await modeledRun(f.config),'MAIN_UNVERIFIABLE');
  assert.ok(!JSON.stringify(f.state.reports).includes('sensitive'));
});
for(const builds of [{},[receipt('unknown')],[{...receipt(),updated_at:null}]])test(`invalid receipt fails safely: ${JSON.stringify(builds)}`,async()=>{
  blocked(await modeledRun(fixture({readBuilds:async()=>builds}).config),'PAGES_RECEIPT_INVALID');
});
test('transient API failure retries inside budget; never treats unreadability as success',async()=>{
  const f=fixture();f.config.readBuilds=async()=>{if(++f.state.buildCalls<3)throw new PagesReadyError('READ_UNAVAILABLE',true);return [receipt()];};
  assert.equal((await modeledRun(f.config)).syncInvocations,1);assert.equal(f.state.buildCalls,3);
});
test('Production 403 fails, and 404/500 cannot stand in for matching CSV/HTML',async()=>{
  blocked(await modeledRun(fixture({readProduction:async()=>({status:403,body:Buffer.from('no')})}).config),'PRODUCTION_INPUT_UNVERIFIABLE');
  for(const status of [404,500])blocked(await modeledRun(fixture({maxAttempts:2,readProduction:async()=>({status,body:Buffer.from('not expected')})}).config),'PAGES_READY_ATTEMPTS_EXHAUSTED');
});
for(const event of ['schedule','workflow_dispatch'])test(`${event} compensates for missed/earlier-failed publication attempt`,async()=>{
  const early=fixture({maxAttempts:1,readBuilds:async()=>[receipt('building')]});blocked(await modeledRun(early.config),'PAGES_READY_ATTEMPTS_EXHAUSTED');
  const later=fixture();assert.equal((await modeledRun(later.config)).syncInvocations,1);
});
test('previous 24-row state interpretation race stays blocked until new root HTML is served',async()=>{
  const dir=mkdtempSync(path.join(tmpdir(),'pages-ready-state-race-'));
  try {
    const old=execFileSync('git',['show','HEAD:index.html'],{encoding:'utf8'}),next=old.replace("'柏林':'Berlin'","'柏林':'Bayern'");assert.notEqual(old,next);
    const csv=Buffer.from('ID,StoreName,StoreType,City,PostalCode,Address,State,Latitude,Longitude,Category,Geekbar,Dojo\n'+Array.from({length:24},(_,i)=>`${90001+i},Synthetic ${i},Kiosk,Berlin,10000,Test address,柏林,52.5,13.3,Test,1,1`).join('\n')+'\n');
    const csvFile=path.join(dir,'synthetic.csv');writeFileSync(csvFile,csv);
    const parse=(name,html)=>{const p=path.join(dir,name);writeFileSync(p,html);return JSON.parse(execFileSync('python3',['scripts/gallery-sync/read-map-catalog.py',csvFile,p],{encoding:'utf8'}));};
    const a=parse('old.html',old),b=parse('next.html',next);assert.equal(a.sourceSha256,b.sourceSha256);assert.equal(b.stores.filter(s=>s.state!==a.stores.find(o=>o.id===s.id).state).length,24);
    const target={csv,source:null,html:Buffer.from(next)},f=fixture({expected:target,maxAttempts:2});
    f.config.readProduction=async({key})=>({status:key==='source'?404:200,body:key==='html'?Buffer.from(old):target[key]});
    blocked(await modeledRun(f.config),'PAGES_READY_ATTEMPTS_EXHAUSTED');
    const ready=fixture({expected:target});assert.equal((await modeledRun(ready.config)).syncInvocations,1);
  } finally {rmSync(dir,{recursive:true,force:true});}
});
test('named data release receipt is distinct from a later HTML/Preview HEAD receipt',async()=>{
  const f=fixture({dataReleaseRevision:B});
  f.config.readBuilds=async()=>[receipt(),receipt(++f.state.buildCalls===1?'building':'built',B)];
  const r=await modeledRun(f.config);assert.equal(r.syncInvocations,1);assert.equal(f.state.buildCalls,2);
  assert.equal(r.result.receipt.commit,A);assert.equal(r.result.dataReceipt.commit,B);
});
test('current HEAD built cannot replace missing/failed exact data-release receipt',async()=>{
  blocked(await modeledRun(fixture({dataReleaseRevision:B,maxAttempts:2}).config),'PAGES_READY_ATTEMPTS_EXHAUSTED');
  blocked(await modeledRun(fixture({dataReleaseRevision:B,readBuilds:async()=>[receipt(),receipt('errored',B)]}).config),'PAGES_BUILD_FAILED');
  blocked(await modeledRun(fixture({dataReleaseRevision:undefined}).config),'DATA_RELEASE_REVISION_REQUIRED');
});
test('receipt adapter follows bounded pages for an older exact data release',async()=>{
  let calls=0;
  const clients=readOnlyClients({token:'synthetic',fetch:async()=>({status:200,arrayBuffer:async()=>Buffer.from(JSON.stringify(++calls===1?[receipt(),...Array.from({length:99},()=>receipt('built','c'.repeat(40)))]:[receipt('built',B)]))})});
  const rows=await clients.readBuilds({remainingMs:1000,requiredRevisions:[A,B]});assert.equal(calls,2);assert.ok(rows.some(r=>r.commit===B));
});
test('checkout snapshot rejects dirty CSV, marker or HTML before network access',()=>{
  const git=args=>args[0]==='ls-tree'?Buffer.from(Object.values(FILES).join('\0')+'\0'):expected[Object.keys(FILES).find(k=>args[1].endsWith(':'+FILES[k]))];
  for(const dirty of Object.keys(FILES))assert.throws(()=>checkoutInputs(A,git,name=>name===FILES[dirty]?Buffer.from('dirty'):expected[Object.keys(FILES).find(k=>FILES[k]===name)]),/CHECKOUT_INPUT_MISMATCH/);
  assert.deepEqual(checkoutInputs(A,git,name=>expected[Object.keys(FILES).find(k=>FILES[k]===name)]),expected);
});
test('untracked provenance marker cannot masquerade as committed input',()=>{
  const git=args=>args[0]==='ls-tree'?Buffer.from([FILES.csv,FILES.html].join('\0')+'\0'):expected[args[1].endsWith(':index.html')?'html':'csv'];
  assert.throws(()=>checkoutInputs(A,git,name=>expected[Object.keys(FILES).find(k=>FILES[k]===name)]),/CHECKOUT_INPUT_MISMATCH/);
});
test('HTTP adapters only GET; GitHub token is never sent to Production',async()=>{
  const calls=[],clients=readOnlyClients({token:'synthetic-test-token',fetch:async(url,options)=>{calls.push({url,options});return {status:200,arrayBuffer:async()=>Buffer.from(url.includes('api.github.com')?'[]':'published')};},git:()=>A+'\trefs/heads/main\n'});
  assert.equal(clients.readMain(100),A);await clients.readBuilds({remainingMs:100});await clients.readProduction({filename:FILES.csv,revision:A,attempt:1,remainingMs:100});
  assert.ok(calls.every(c=>c.options.method==='GET'&&c.options.redirect==='error'));
  assert.equal(calls[0].options.headers.Authorization,'Bearer synthetic-test-token');assert.equal(calls[1].options.headers.Authorization,undefined);
  assert.ok(calls.every(c=>!c.url.includes('cloudflare')&&!c.url.includes('/d1/')));
});
for(const status of [401,403,404])test(`Pages API ${status} cannot be replaced by trust in main`,async()=>{
  const clients=readOnlyClients({token:'synthetic',fetch:async()=>({status,arrayBuffer:async()=>Buffer.from('denied')})});
  await assert.rejects(clients.readBuilds({remainingMs:100}),/PAGES_API_UNVERIFIABLE/);
});
test('read adapter network errors are bounded retryable failures, not exposed raw errors',async()=>{
  const c=readOnlyClients({token:'synthetic',fetch:async()=>{throw Error('secret response');}});
  await assert.rejects(c.readBuilds({remainingMs:100}),e=>e.code==='READ_UNAVAILABLE'&&e.retryable&&!e.message.includes('secret'));
});
test('CLI writes ready output only after success; failed receipt leaves output unset and evidence blocked',()=>{
  const dir=mkdtempSync(path.join(tmpdir(),'pages-ready-cli-'));
  try {
    for(const [key,name] of Object.entries(FILES))writeFileSync(path.join(dir,name),expected[key]);
    const preload=path.join(dir,'mock.mjs');
    writeFileSync(preload,`import cp from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
import {readFileSync} from 'node:fs';
const sha='${A}';
cp.execFileSync=(command,args,options={})=>{
 if(command!=='git')throw Error('NON_READ_COMMAND_FORBIDDEN');
 let result;
 if(args[0]==='rev-parse')result=args[1]==='HEAD'?sha+'\\n':'false\\n';
 else if(args[0]==='ls-tree')result=${JSON.stringify(Object.values(FILES).join('\0')+'\0')};
 else if(args[0]==='show')return readFileSync(args[1].split(':').slice(1).join(':'));
 else if(args[0]==='log')result=sha+'\\n';
 else if(args[0]==='ls-remote')result=sha+'\\trefs/heads/main\\n';
 else throw Error('NON_READ_GIT_FORBIDDEN');
 return options.encoding?result:Buffer.from(result);
};
syncBuiltinESMExports();
globalThis.fetch=async(url,options)=>{
 if(options.method!=='GET')throw Error('NON_GET_FORBIDDEN');
 if(url.startsWith('https://api.github.com/'))return new Response(JSON.stringify([{commit:sha,status:process.env.MOCK_BUILD_STATUS,updated_at:'2026-10-23T00:00:00Z'}]));
 if(url.startsWith('https://map.vplink-automaten.de/'))return new Response(readFileSync(decodeURIComponent(new URL(url).pathname.slice(1))));
 throw Error('NETWORK_FORBIDDEN');
};`);
    const gate=path.resolve('scripts/gallery-sync/pages-ready.mjs'),output=path.join(dir,'step-output');
    const env={...process.env,GITHUB_REPOSITORY:'bds109/vplink-network-map',GITHUB_EVENT_NAME:'push',GITHUB_TOKEN:'synthetic-cli-token',GITHUB_OUTPUT:output};delete env.CLOUDFLARE_API_TOKEN;
    assert.throws(()=>execFileSync(process.execPath,['--import',preload,gate],{cwd:dir,env:{...env,MOCK_BUILD_STATUS:'errored'},stdio:'pipe'}));
    assert.throws(()=>readFileSync(output));
    assert.equal(JSON.parse(readFileSync(path.join(dir,'gallery-sync-evidence/pages-ready.json'))).status,'BLOCKED');
    execFileSync(process.execPath,['--import',preload,gate],{cwd:dir,env:{...env,MOCK_BUILD_STATUS:'built'},stdio:'pipe'});
    assert.equal(readFileSync(output,'utf8'),'ready=true\n');
    const evidence=readFileSync(path.join(dir,'gallery-sync-evidence/pages-ready.json'),'utf8');
    assert.equal(JSON.parse(evidence).status,'READY');assert.ok(!evidence.includes('synthetic-cli-token'));
  } finally {rmSync(dir,{recursive:true,force:true});}
});
test('default gate budget fits inside 4-minute gate step and 15-minute job',()=>{
  assert.equal(BUDGET_MS,180000);assert.ok(BUDGET_MS<4*60000&&15*60000-4*60000>=11*60000);
  const source=readFileSync('scripts/gallery-sync/pages-ready.mjs','utf8');assert.ok(!source.includes("from './sync.mjs'"));assert.ok(!source.includes('api.cloudflare.com'));
});
