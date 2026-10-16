import fs from 'node:fs/promises';
import {Workbook} from '@oai/artifact-tool';

const dir = new URL('../../output/mock_data/',import.meta.url);
const dataset = JSON.parse(await fs.readFile(new URL('ship_supply_mock_10.json',dir),'utf8'));
const fields=['문서번호','발행일자','공급자','공급받는자','선박명','공급일','공급장소','통화',
              '번호','품목코드','품명','규격','수량','단위','단가','금액'];
const rows=dataset.documents.flatMap(d=>d.품목.map(p=>[
  d.문서번호,d.발행일자,d.공급자.상호,d.공급받는자.상호,d.선박명,d.공급일,d.공급장소,d.통화,
  p.번호,p.품목코드,p.품명,p.규격,p.수량,p.단위,p.단가,p.금액
]));
const wb=Workbook.create();
const sheet=wb.worksheets.add('Items');
sheet.getRange(`A1:P${rows.length+1}`).values=[fields,...rows];
sheet.getRange(`A1:P${rows.length+1}`).format.font={name:'Arial Unicode MS',size:10};
sheet.getRange('A1:P1').format={fill:'#20364D',font:{bold:true,color:'#FFFFFF'}};
sheet.getRange('A:A').format.columnWidth=34;
sheet.getRange('B:J').format.columnWidth=24;
sheet.getRange('K:L').format.columnWidth=32;
sheet.getRange('M:P').format.columnWidth=15;
sheet.getRange(`M2:M${rows.length+1}`).setNumberFormat('0');
sheet.getRange(`O2:P${rows.length+1}`).setNumberFormat('#,##0');
sheet.freezePanes.freezeRows(1);
sheet.showGridLines=false;
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Items!I1:P4',tableMaxRows:4,tableMaxCols:8,maxChars:1800})).ndjson);
const values=sheet.getRange(`A1:P${rows.length+1}`).values;
if(values.length!==161) throw Error('Expected 160 item rows plus header');
for(const row of values.slice(1)){
  if(row[12]*row[14]!==row[15]) throw Error('Amount mismatch');
}
// CSV는 표시 서식/수식을 보관하지 않으므로 검증된 셀의 원시 값을 내보낸다.
const escape=v=>{const s=String(v??'');return /[",\r\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;};
await fs.writeFile(new URL('ship_supply_mock_items_160.csv',dir),'\uFEFF'+values.map(r=>r.map(escape).join(',')).join('\r\n')+'\r\n','utf8');
const image=await wb.render({sheetName:'Items',range:'I1:P7',scale:1.5,format:'png'});
await fs.writeFile(new URL('mock_csv_preview.png',import.meta.url),new Uint8Array(await image.arrayBuffer()));
console.log('CSV exported: 160 rows');
