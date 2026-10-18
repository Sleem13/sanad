// Physical page coordinates stay LTR; each text line carries its own direction.
const escapeXML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
export function pageSVG(page){
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
