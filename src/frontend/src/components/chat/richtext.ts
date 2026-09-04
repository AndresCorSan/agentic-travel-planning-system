// Minimal safe renderer: escapes HTML, then supports **bold**,
// "- " list items, and "**...**"-only lines as subheads.
export function renderRich(text: string): string {
  const esc = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  const inline = (s: string) => s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  const lines = esc.split('\n');
  let html = '';
  let inList = false;
  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      continue;
    }
    if (/^[-•]\s+/.test(t)) {
      if (!inList) {
        html += '<ul>';
        inList = true;
      }
      html += `<li>${inline(t.replace(/^[-•]\s+/, ''))}</li>`;
    } else if (/^\*\*.+\*\*$/.test(t)) {
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      html += `<p class="subhead">${inline(t)}</p>`;
    } else {
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      html += `<p>${inline(t)}</p>`;
    }
  }
  if (inList) html += '</ul>';
  return html;
}
