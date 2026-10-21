// Physical page coordinates stay LTR; each text line carries its own direction.
const escapeXML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
export function pageSVG(page){
 // Whole-page mode has no detected line coordinates. Use a flowing transcript,
 // never stretch its lines across the source bounding box.
 if(page.regions.some(r=>r.flags?.includes('whole_page_only'))){
  const rows=page.regions.flatMap(r=>(r.text||'').split(/\r?\n/)).filter(t=>t.trim());
  const counts=new Map();for(const row of rows){const key=row.trim();counts.set(key,(counts.get(key)||0)+1);}
  const repeated=[...counts.values()].some(n=>n>=Math.max(4,rows.length*.6));
  const shown=repeated?['Unreliable OCR: repeated output. Obtain a clearer source or transcribe manually.']:rows.flatMap(row=>row.match(/.{1,75}(?:\s|$)|.{1,75}/gu)||[]);
  const width=900,height=Math.max(150,80+shown.length*28);
  const text=shown.map((line,i)=>`<text x="${/[\u0590-\u08ff]/.test(line)?width-24:24}" y="${85+i*28}" direction="${/[\u0590-\u08ff]/.test(line)?'rtl':'ltr'}" font-size="18">${escapeXML(line)}</text>`).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="Unpositioned OCR transcript"><title>Unpositioned transcript — not source page layout</title><rect width="100%" height="100%" fill="white"/><g font-family="Tahoma, Arial, sans-serif" fill="#111"><text x="24" y="30" font-size="16">${repeated?'Repeated generation rejected':'Whole-page OCR — no detected line positions; review against original'}</text>${text}</g></svg>`;
 }
 const lines=[...page.regions].sort((a,b)=>(a.reading_order??Infinity)-(b.reading_order??Infinity)).filter(r=>r.text?.trim()).map(r=>{
  const [x,y,x1,y1]=r.bbox;const width=x1-x,height=y1-y;
  if(r.cells?.length){
   const rows=Math.max(...r.cells.map(c=>c.row+c.rowspan));
   const cols=Math.max(...r.cells.map(c=>c.col+c.colspan));
   return r.cells.map(cell=>{
    const left=x+width*cell.col/cols,top=y+height*cell.row/rows;
    const w=width*cell.colspan/cols,h=height*cell.rowspan/rows;
    const text=cell.text||'',rtl=/[\u0590-\u08ff]/.test(text);
    return `<rect x="${left}" y="${top}" width="${w}" height="${h}" fill="none" stroke="#777" stroke-width=".5"/><text x="${rtl?left+w-2:left+2}" y="${top+h/2}" direction="${rtl?'rtl':'ltr'}" dominant-baseline="central" font-size="${Math.min(h*.65,w/Math.max(text.length,1)*1.8)}">${escapeXML(text)}</text>`;
   }).join('\n');
  }
  const rows=r.text.split(/\r?\n/).filter(t=>t.trim());
  return rows.map((text,index)=>{
   const rtl=/[\u0590-\u08ff]/.test(text);
   const lineHeight=height/rows.length;
   return `<text x="${rtl?x1:x}" y="${y+lineHeight*(index+.5)}" direction="${rtl?'rtl':'ltr'}" text-anchor="start" dominant-baseline="central" font-size="${lineHeight*.82}" textLength="${width}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">${escapeXML(text)}</text>`;
  }).join('\n');
 }).join('\n');
 return `<svg xmlns="http://www.w3.org/2000/svg" width="${page.width}" height="${page.height}" viewBox="0 0 ${page.width} ${page.height}" role="img" aria-label="OCR page layout"><title>OCR transcription — source page positions</title><rect width="100%" height="100%" fill="white"/><g fill="#111" font-family="Tahoma, Arial, sans-serif">${lines}</g></svg>`;
}
