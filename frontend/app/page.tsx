export default function Home() {
  return (
    <div style={{ padding: '40px', fontFamily: 'sans-serif', backgroundColor: '#0f172a', color: '#fff', minHeight: '100vh' }}>
      <h1 style={{ color: '#38bdf8' }}>AI Infrastructure Memory</h1>
      <p>Version 0.1</p>
      <div style={{ marginTop: '20px', padding: '20px', border: '1px solid #334155', borderRadius: '8px' }}>
        <h3>System Status</h3>
        <ul>
          <li>Backend: <span style={{ color: '#4ade80' }}>Running</span></li>
          <li>Database: <span style={{ color: '#fbbf24' }}>Pending</span></li>
          <li>Redis: <span style={{ color: '#fbbf24' }}>Pending</span></li>
        </ul>
      </div>
    </div>
  );
}
