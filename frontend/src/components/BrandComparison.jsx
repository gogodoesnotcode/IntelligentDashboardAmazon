const ASPECTS = ["wheels", "handle", "zipper", "material", "size", "durability"];

export default function BrandComparison({ summary }) {
  const brands = Object.values(summary.brands);

  return (
    <div className="screen">
      <h2>Brand comparison</h2>

      <div className="card table-scroll">
        <h3>Aspect scores</h3>
        <table>
          <thead>
            <tr>
              <th>Aspect</th>
              {brands.map((b) => (
                <th key={b.brand}>{b.brand}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ASPECTS.map((aspect) => (
              <tr key={aspect}>
                <td className="row-label">{aspect}</td>
                {brands.map((b) => {
                  const a = b.aspect_scores?.[aspect];
                  return <td key={b.brand}>{a ? a.score.toFixed(1) : "—"}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card table-scroll">
        <h3>Value for money</h3>
        <table>
          <thead>
            <tr>
              <th>Brand</th>
              <th>Score</th>
              <th>Price band</th>
              <th>Avg price</th>
            </tr>
          </thead>
          <tbody>
            {brands.map((b) => (
              <tr key={b.brand}>
                <td>{b.brand}</td>
                <td>{b.value_for_money?.score ?? "—"}</td>
                <td>{b.value_for_money?.price_band ?? "—"}</td>
                <td>{b.value_for_money?.avg_price != null ? `₹${b.value_for_money.avg_price}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
