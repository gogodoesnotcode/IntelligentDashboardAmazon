// Wraps quoted review snippets, rupee amounts, and (optionally) known brand
// names in LLM-generated prose so the important bits stand out instead of
// the whole paragraph reading as one flat block of text.
export function highlightText(text, boldTerms = []) {
  if (!text) return text;

  const termPattern = boldTerms.length
    ? "|" + boldTerms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")
    : "";
  const re = new RegExp(`("[^"]+"|₹[\\d,]+(?:\\.\\d+)?${termPattern})`, "g");

  return text.split(re).map((part, i) => {
    if (!part) return null;
    if (/^".*"$/.test(part)) {
      return (
        <em key={i}>
          <mark className="quote">{part}</mark>
        </em>
      );
    }
    if (/^₹[\d,]+/.test(part) || boldTerms.includes(part)) {
      return <strong key={i}>{part}</strong>;
    }
    return part;
  });
}
