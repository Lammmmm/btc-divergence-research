import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(fileURLToPath(import.meta.url));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.resolve(root,'../outputs/BTCUSDT_20组单指标回测.xlsx')));
console.log((await wb.inspect({kind:'table',range:'结果排名!A23:J26',include:'values,formulas',tableMaxRows:4,tableMaxCols:10,maxChars:1800})).ndjson);
for(const [s,r,file] of [['回测计划','A30:I51','single_plan_inputs'],['结果排名','A23:J33','single_daily'],['逐笔明细','A4:I12','single_trade_dates']]){
const image=await wb.render({sheetName:s,range:r,scale:1.2,format:'png'});
await fs.writeFile(path.join(root,file+'.png'),new Uint8Array(await image.arrayBuffer()));
}
