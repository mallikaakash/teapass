import styles from "./passport.module.css";

const ROWS = [
  { label: "Origin", value: "Dikom Tea Estate, Assam" },
  { label: "People", value: "Picker section 4B · signed collection" },
  { label: "Process", value: "Wither → roll → oxidize → dry" },
  { label: "Evidence", value: "Lab pass · mass balance verified" },
  { label: "Claims", value: "First flush · single estate" },
];

export function Passport() {
  return (
    <div className={styles.passport}>
      <header>
        <p className={styles.eyebrow}>Tea passport</p>
        <h3>DTE-2024-0512</h3>
      </header>
      <ul>
        {ROWS.map((row) => (
          <li key={row.label}>
            <span>{row.label}</span>
            <strong>{row.value}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}
