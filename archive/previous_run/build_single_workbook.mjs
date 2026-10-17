import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(root,'single_backtest.json'),'utf8'));
const out=path.resolve(root,'../outputs');
const wb=Workbook.create();
const summary=wb.worksheets.add('结果排名');
const plan=wb.worksheets.add('回测计划');
const calc=wb.worksheets.add('统计计算');
const detail=wb.worksheets.add('逐笔明细');
const labels={Hist:'MACD Histogram',Stoch:'Stochastic',MOM:'Momentum',VWMACD:'VWmacd',CMF:'Chaikin Money Flow',MFI:'Money Flow Index'};
const label=x=>labels[x]||x;
const fmt='0.00%;(0.00%);"—"';
const cash='#,##0.00;(#,##0.00);"—"';
const color='#183B56';
function base(s,last,lastCol){
 s.showGridLines=false;
 s.getRange(`A1:${lastCol}${last}`).format.font={name:'Arial',size:11,color:'#1E293B'};
 s.getRange(`A1:${lastCol}${last}`).format.rowHeight=23;
 s.getRange(`A1:${lastCol}${last}`).format.verticalAlignment='center';
}
function title(s,row,text){s.getRange(`A${row}`).values=[[text]];s.getRange(`A${row}`).format.font={name:'Arial',size:16,bold:true,color};s.getRange(`A${row}`).format.rowHeight=29;}
function header(s,row,cols){
 const r=s.getRangeByIndexes(row-1,0,1,cols.length);r.values=[cols];
 r.format={fill:color,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:29,horizontalAlignment:'center',verticalAlignment:'center'};
}
function stripes(s,start,end,col){for(let r=start;r<=end;r++)if((r-start)%2===1)s.getRange(`A${r}:${col}${r}`).format.fill='#F1F5F9';}
function pct(s,range){s.getRange(range).setNumberFormat(fmt);}
function note(s,row,text){s.getRange(`A${row}`).values=[[text]];s.getRange(`A${row}`).format.font={name:'Arial',size:11,color:'#526475'};}
base(plan,66,'I');plan.tabColor='#527B96';
title(plan,2,'BTCUSDT 永续：20组独立回测计划');
note(plan,3,'已完成。每组只启用一个指标；4H和1D各10组；不测试组合。');
note(plan,4,'各组独立账户；组内多空共用一个仓位，持仓期间忽略任何新信号。');
header(plan,6,['任务编号','周期','唯一启用指标','正式评估区间(UTC)','持有根数','方向','持仓上限','状态','完成交易数']);
const mains=data.summary.filter(s=>s.period==='全期');
const smap=new Map(data.summary.map((s,i)=>[s.group,i+4]));
plan.getRange('A7:I26').values=mains.map((s,i)=>[`TEST-${String(i+1).padStart(2,'0')}`,s.tf,label(s.name),'2021-01-01～2026-10-15',10,'多 / 空',1,'已完成',null]);
plan.getRange('I7:I26').formulas=mains.map(s=>[`='统计计算'!I${smap.get(s.group)}`]);
stripes(plan,7,26,'I');
plan.tables.add('A6:I26',true,'TestPlan');
header(plan,30,['固定参数','设定值','说明']);
const assumptions=[
 ['品种','BINANCE BTCUSDT','USDT本位永续；使用合约成交价K线'],
 ['初始权益（USDT）',10000,'每组、每段从同一起点开始；复投'],
 ['单边手续费',0.0005,'假设费率；预留开仓手续费后使用剩余权益作为名义金额'],
 ['单边滑点',0.0002,'开仓与平仓均按不利方向调整价格'],
 ['持有根数',10,'4H持有40小时；1D持有10天；无止盈止损'],
 ['背离类型','Regular','只测普通顶/底背离；隐藏背离不在本轮范围'],
 ['价格源','Close','CCI与MFI也按原脚本使用close'],
 ['Pivot Period',5,'历史拐点必须已被右侧5根确认'],
 ['检查拐点数量',10,'Maximum Pivot Points to Check'],
 ['最大回看K线',100,'Maximum Bars to Check'],
 ['等待确认','开启','Don’t Wait for Confirmation不勾选；只记录收盘有效信号'],
 ['最少背离数量',1,'每组只有一个指标，不附加共振过滤'],
 ['入场','次根开盘','信号出现当根收盘后，次根开盘入场'],
 ['退出','第10根收盘','不开提前反向单；持仓结束后才允许下一笔'],
 ['预热区间','2020全年','仅预热，不计入正式收益'],
 ['前段复核','2021～2024','单独从10000USDT开始；到区间末仍未完成的信号不入场'],
 ['后段复核','2025～2026-10-15','数据已在上一轮看过，不是全新盲测样本'],
 ['资金费','历史费率计入','缺失标记价时用当时4H开盘价代理；费用为估算'],
 ['最大回撤','收盘权益采样','含持仓浮盈亏及已发生费用；不是盘中最高回撤'],
 ['外部指标','不测试','External Indicator是输入接口，没有独立指标定义'],
 ['表格属性','固定回测报告','修改信号、费用或持有期需重新运行回测，不是参数模拟器'],
];
plan.getRange('A31:C51').values=assumptions;
plan.getRange('B32').setNumberFormat(cash);pct(plan,'B33:B34');
note(plan,54,'方向准确率=价格方向正确的交易数/总交易数；扣费胜率=净盈利交易数/总交易数。');
note(plan,55,'累计净收益=(期末权益/初始权益)-1，逐笔复投；不等于每笔收益简单相加。');
note(plan,56,'资金费6342条，其中3100条缺失标记价；两天日线成交量与4H聚合不一致，保留原始周期数据。');
note(plan,57,'本地Python复现原脚本，未与TradingView逐根导出交叉核验；无杠杆、强平、止损模拟。');
note(plan,58,'同组持仓互斥已验证；不同独立实验可使用相同历史时段，不能把20组收益相加。');
note(plan,60,'数据源：Binance USDⓈ-M K线与资金费率（2026-10-16下载并冻结）');
note(plan,61,'https://fapi.binance.com/fapi/v1/klines');
note(plan,62,'https://fapi.binance.com/fapi/v1/fundingRate');
note(plan,63,'策略时序参考：https://www.tradingview.com/pine-script-docs/concepts/strategies/');
for(const [c,w] of Object.entries({A:24,B:27,C:29,D:30,E:12,F:13,G:13,H:13,I:15}))plan.getRange(`${c}1:${c}66`).format.columnWidth=w;
plan.freezePanes.freezeRows(6);

const ts=data.trades, end=ts.length+4;
base(detail,end,'Z');title(detail,2,'逐笔交易：原始执行结果与权益计算');
note(detail,3,'时间均为北京时间。全期、前段、后段是同一实验的不同区间，不能合并统计。费用率和执行价已由回测引擎固定。');
header(detail,4,['组ID','周期','指标','区间','序号','方向','信号K线开盘时间','入场时间','出场时间','原始入场价','原始出场价','含滑点入场价','含滑点出场价','方向收益率','含滑点收益率','手续费率','资金费用率','净收益率','入场前权益','开仓名义金额','净收益USDT','出场后权益','方向命中','净盈利','盈利金额','亏损金额']);
const excelDate=ms=>Math.floor(ms/1000)/86400+25569+8/24;
detail.getRange(`A5:Z${end}`).values=ts.map(t=>[t.group,t.tf,label(t.name),t.period,t.seq,t.side,excelDate(t.signal_time),excelDate(t.entry_time),excelDate(t.exit_time),t.entry_raw,t.exit_raw,t.entry,t.exit,null,null,t.fees,t.funding,null,null,null,null,null,null,null,null,null]);
detail.getRange(`N5:O${end}`).formulas=ts.map((t,i)=>{const r=i+5;return [`=IF(F${r}="多",1,-1)*(K${r}/J${r}-1)`,`=IF(F${r}="多",1,-1)*(M${r}/L${r}-1)`]});
detail.getRange(`R5:Z${end}`).formulas=ts.map((t,i)=>{const r=i+5;return [`=O${r}-P${r}-Q${r}`,t.seq===1?"='回测计划'!$B$32":`=V${r-1}`,`=S${r}/(1+'回测计划'!$B$33)`,`=T${r}*R${r}`,`=S${r}+U${r}`,`=IF(N${r}>0,1,0)`,`=IF(U${r}>0,1,0)`,`=MAX(U${r},0)`,`=-MIN(U${r},0)`]});
detail.getRange(`G5:I${end}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');
detail.getRange(`J5:M${end}`).setNumberFormat(cash);pct(detail,`N5:R${end}`);detail.getRange(`S5:V${end}`).setNumberFormat(cash);detail.getRange(`Y5:Z${end}`).setNumberFormat(cash);
detail.getRange(`A1:A${end}`).format.columnWidth=29;detail.getRange(`B1:B${end}`).format.columnWidth=9;detail.getRange(`C1:C${end}`).format.columnWidth=26;detail.getRange(`D1:F${end}`).format.columnWidth=9;
detail.getRange(`G1:I${end}`).format.columnWidth=29;detail.getRange(`J1:Z${end}`).format.columnWidth=18;
detail.freezePanes.freezeRows(4);detail.freezePanes.freezeColumns(3);
detail.tables.add(`A4:Z${end}`,true,'TradeLedger');

base(calc,65,'W');title(calc,2,'按组汇总：20个实验 × 3个区间');
header(calc,3,['组ID','周期','指标','区间','原始信号数','持仓忽略数','期末排除数','多空冲突数','交易数','方向正确数','方向准确率','净盈利数','扣费胜率','净收益USDT','累计净收益','期末权益','平均每笔净收益','盈利因子','收盘最大回撤','做多笔数','做空笔数','准确率下界*','准确率上界*']);
const source=(c)=>`'逐笔明细'!$${c}$5:$${c}$${end}`;
calc.getRange('A4:W63').values=data.summary.map(s=>[s.group,s.tf,label(s.name),s.period,s.raw,s.skipped,s.tail,s.conflict,null,null,null,null,null,null,null,null,null,null,s.maxdd,null,null,null,null]);
for(let i=0;i<data.summary.length;i++){
 const r=i+4,key=`$A${r}`,match=source('A');
 calc.getRange(`I${r}:R${r}`).formulas=[[
 `=COUNTIFS(${match},${key})`,`=SUMIFS(${source('W')},${match},${key})`,`=IF(I${r}=0,"n.a.",J${r}/I${r})`,
 `=SUMIFS(${source('X')},${match},${key})`,`=IF(I${r}=0,"n.a.",L${r}/I${r})`,`=SUMIFS(${source('U')},${match},${key})`,
 `=N${r}/'回测计划'!$B$32`,`='回测计划'!$B$32+N${r}`,`=IF(I${r}=0,"n.a.",AVERAGEIFS(${source('R')},${match},${key}))`,
 `=IF(SUMIFS(${source('Z')},${match},${key})=0,"n.a.",SUMIFS(${source('Y')},${match},${key})/SUMIFS(${source('Z')},${match},${key}))`
 ]];
 calc.getRange(`T${r}:W${r}`).formulas=[[
 `=COUNTIFS(${match},${key},${source('F')},"多")`,`=COUNTIFS(${match},${key},${source('F')},"空")`,
 `=(K${r}+1.96^2/(2*I${r})-1.96*SQRT(K${r}*(1-K${r})/I${r}+1.96^2/(4*I${r}^2)))/(1+1.96^2/I${r})`,
 `=(K${r}+1.96^2/(2*I${r})+1.96*SQRT(K${r}*(1-K${r})/I${r}+1.96^2/(4*I${r}^2)))/(1+1.96^2/I${r})`
 ]];
}
for(const c of ['K','M','O','Q','S','V','W'])pct(calc,`${c}4:${c}63`);
for(const c of ['N','P'])calc.getRange(`${c}4:${c}63`).setNumberFormat(cash);
calc.getRange('R4:R63').setNumberFormat('0.00');
calc.getRange('A1:A65').format.columnWidth=29;calc.getRange('B1:B65').format.columnWidth=9;calc.getRange('C1:C65').format.columnWidth=27;calc.getRange('D1:D65').format.columnWidth=10;calc.getRange('E1:W65').format.columnWidth=18;
note(calc,65,'*95% Wilson描述性区间，未修正行情相关性和多重比较。收盘最大回撤由逐K线权益引擎计算，非仅平仓回撤。');
calc.tables.add('A3:W63',true,'Statistics');calc.freezePanes.freezeRows(3);

base(summary,76,'J');summary.tabColor=color;title(summary,2,'BTCUSDT 单指标背离回测结果');
note(summary,3,'每组初始10000USDT；普通背离；持有10根；单仓不重叠；手续费、滑点、资金费已计入。');
note(summary,4,'默认按累计净收益排序，方向准确率单独排名。4H=40小时，1D=10天。未测试组合。');
const sections=[['4H','全期',6],['1D','全期',23],['4H','后段',40],['1D','后段',57]];
for(const [tf,period,row] of sections){
 note(summary,row-1,`${tf} ${period==='全期'?'2021-01-01～2026-10-15':'2025-01-01～2026-10-15（从10000重新起算）'}`);
 header(summary,row,['单独启用指标','交易数','方向准确率','扣费胜率','累计净收益','期末USDT','收盘最大回撤','每笔平均净收益','收益名次','准确率名次']);
 const rows=data.summary.filter(s=>s.tf===tf&&s.period===period).sort((a,b)=>b.total_return-a.total_return);
 for(let i=0;i<rows.length;i++){
  const s=rows[i],r=row+1+i,c=smap.get(s.group);
  summary.getRange(`A${r}:J${r}`).formulas=[[
   `='统计计算'!C${c}`,`='统计计算'!I${c}`,`='统计计算'!K${c}`,`='统计计算'!M${c}`,`='统计计算'!O${c}`,`='统计计算'!P${c}`,`='统计计算'!S${c}`,`='统计计算'!Q${c}`,
   `=1+COUNTIFS($E$${row+1}:$E$${row+10},">"&E${r})`,`=1+COUNTIFS($C$${row+1}:$C$${row+10},">"&C${r})`
  ]];
 }
 stripes(summary,row+1,row+10,'J');
 pct(summary,`C${row+1}:E${row+10}`);pct(summary,`G${row+1}:H${row+10}`);summary.getRange(`F${row+1}:F${row+10}`).setNumberFormat(cash);
 summary.getRange(`E${row+1}:E${row+10}`).conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{font:{color:'#B42318'}}});
 summary.getRange(`B${row+1}:B${row+10}`).conditionalFormats.add('cellIs',{operator:'lessThan',formula:30,format:{fill:'#FFF2CC'}});
 summary.tables.add(`A${row}:J${row+10}`,true,`Rank${tf}${period==='全期'?'Full':'Recent'}`);
}
note(summary,70,'黄色交易数：少于30笔。日线尤其要结合样本量；收益最高与准确率最高可能是不同指标。');
note(summary,71,'全期为连续账户；前段/后段各自重新启动，跨区间尚未完成交易不纳入分段。');
note(summary,72,'最大回撤仅按K线收盘权益采样，可能低于盘中回撤；本轮未模拟杠杆、强平和止损。');
note(summary,73,'本表是固定规则报告。算法由本地Python复现，未与TradingView逐根核验。');
summary.getRange('A1:A76').format.columnWidth=28;summary.getRange('B1:B76').format.columnWidth=11;
summary.getRange('C1:G76').format.columnWidth=17;summary.getRange('H1:H76').format.columnWidth=21;summary.getRange('I1:J76').format.columnWidth=14;
summary.freezePanes.freezeRows(6);
wb.recalculate();
const values=calc.getRange('I4:W63').values;
let maxError=0;
for(let i=0;i<values.length;i++){
 const s=data.summary[i],v=values[i];
 for(const [idx,expected] of [[0,s.n],[2,s.hit],[4,s.net_win],[6,s.total_return],[7,s.ending],[8,s.mean_net],[10,s.maxdd],[11,s.long_count],[12,s.short_count]]){
  if(typeof v[idx]!=='number')throw new Error(`Non-numeric summary ${s.group} col ${idx}: ${v[idx]}`);
  const e=Math.abs(v[idx]-expected);maxError=Math.max(maxError,e);if(e>1e-6)throw new Error(`Mismatch ${s.group}: ${idx} ${v[idx]} vs ${expected}`);
 }
}
// Demonstrate summary propagation using one source-price perturbation, then restore.
const saved=detail.getRange('K5').values[0][0];const before=detail.getRange('N5').values[0][0];
detail.getRange('K5').values=[[saved*1.01]];
if(detail.getRange('N5').values[0][0]===before)throw new Error('Formula recalculation failed');
detail.getRange('K5').values=[[saved]];wb.recalculate();
console.log('INDEPENDENT_COMPARISON',JSON.stringify({groups:values.length,maxAbsoluteError:maxError}));
console.log((await wb.inspect({kind:'table',range:'结果排名!A6:J9',include:'values,formulas',tableMaxRows:4,tableMaxCols:10,maxChars:2500})).ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'final formula error scan',maxChars:2000});
console.log(errors.ndjson);
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(out,'BTCUSDT_20组单指标回测.xlsx'));
for(const [name,range,file] of [['结果排名','A5:J16','single_summary'],['回测计划','A2:I15','single_plan'],['统计计算','A2:M12','single_stats'],['逐笔明细','A4:I12','single_trade_dates']]){
 const p=await wb.render({sheetName:name,range,scale:1.3,format:'png'});
 await fs.writeFile(path.join(root,`${file}.png`),new Uint8Array(await p.arrayBuffer()));
}
await fs.writeFile(path.join(root,'single_workbook_checks.json'),JSON.stringify({groups:60,maxAbsoluteError:maxError,formulaErrors:errors.ndjson},null,2));
console.log('SAVED',path.join(out,'BTCUSDT_20组单指标回测.xlsx'));
