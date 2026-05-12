import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, AlertTriangle, CheckCircle2, Clipboard, GitBranch, Loader2, Search } from 'lucide-react';
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from 'recharts';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function api(path, options) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || 'Request failed');
  }
  return data;
}

function scoreTone(score) {
  if (score >= 80) return 'great';
  if (score >= 60) return 'ok';
  return 'risk';
}

function Home({ onStart }) {
  const [repoUrl, setRepoUrl] = useState('https://github.com/facebook/react');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const created = await api('/api/analysis', {
        method: 'POST',
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      onStart(created.job_id, created.report_url);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell home">
      <section className="intro">
        <div className="brand">
          <GitBranch size={34} />
          <span>Repo Health</span>
        </div>
        <h1>GitHub 仓库代码健康度分析平台</h1>
        <p>粘贴 public repo 地址，后台异步克隆最近 100 个 commit，生成可分享的 7 天有效报告。</p>
      </section>
      <form className="searchPanel" onSubmit={submit}>
        <label htmlFor="repo">Repository URL</label>
        <div className="inputRow">
          <input
            id="repo"
            value={repoUrl}
            onChange={(event) => setRepoUrl(event.target.value)}
            placeholder="https://github.com/owner/repo"
          />
          <button disabled={loading} type="submit" title="Start analysis">
            {loading ? <Loader2 className="spin" size={20} /> : <Search size={20} />}
            <span>分析</span>
          </button>
        </div>
        {error && <div className="error"><AlertTriangle size={18} />{error}</div>}
      </form>
    </main>
  );
}

function ProgressPage({ jobId, onComplete }) {
  const [job, setJob] = useState(null);

  useEffect(() => {
    let stopped = false;
    async function tick() {
      try {
        const next = await api(`/api/analysis/${jobId}`);
        if (stopped) return;
        setJob(next);
        if (next.status === 'completed') {
          onComplete(next.report_id);
          return;
        }
      } catch (err) {
        setJob({ status: 'failed', step: 'Failed', progress: 100, error: err.message });
      }
      setTimeout(tick, 1800);
    }
    tick();
    return () => {
      stopped = true;
    };
  }, [jobId, onComplete]);

  const status = job?.status || 'queued';
  return (
    <main className="shell progressView">
      <div className="statusIcon">
        {status === 'failed' ? <AlertTriangle size={42} /> : <Loader2 className="spin" size={42} />}
      </div>
      <h1>{status === 'failed' ? '分析失败' : '正在分析仓库'}</h1>
      <p>{job?.step || 'Queued'}</p>
      <div className="progressBar">
        <span style={{ width: `${job?.progress || 0}%` }} />
      </div>
      <strong>{job?.progress || 0}%</strong>
      {job?.error && <div className="error"><AlertTriangle size={18} />{job.error}</div>}
    </main>
  );
}

function ScoreRadar({ breakdown }) {
  const data = Object.entries(breakdown).map(([name, score]) => ({ name, score }));
  return (
    <div className="chartBox">
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="name" tick={{ fill: '#45505f', fontSize: 12 }} />
          <Radar dataKey="score" stroke="#246bfe" fill="#246bfe" fillOpacity={0.25} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CommitHeatmap({ weeks }) {
  const max = Math.max(1, ...weeks.map((item) => item.commits));
  return (
    <div className="heatmap">
      {weeks.map((item) => {
        const level = Math.ceil((item.commits / max) * 4);
        return <span key={item.week} className={`heat level${level}`} title={`${item.week}: ${item.commits}`} />;
      })}
    </div>
  );
}

function DetailSection({ title, children, defaultOpen = false }) {
  return (
    <details className="detail" open={defaultOpen}>
      <summary>{title}</summary>
      <div>{children}</div>
    </details>
  );
}

function ResultPage({ reportId }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api(`/api/reports/${reportId}`).then(setReport).catch((err) => setError(err.message));
  }, [reportId]);

  const shareUrl = window.location.href;
  const radar = useMemo(() => report?.score_breakdown || {}, [report]);

  if (error) {
    return <main className="shell"><div className="error"><AlertTriangle size={18} />{error}</div></main>;
  }
  if (!report) {
    return <main className="shell progressView"><Loader2 className="spin" size={38} /><p>加载报告...</p></main>;
  }

  return (
    <main className="shell result">
      <header className="resultHeader">
        <div>
          <div className="eyebrow"><GitBranch size={16} />{report.normalized_repo}</div>
          <h1>代码健康度报告</h1>
          <p>{report.language} · {new Date(report.analyzed_at).toLocaleString()}</p>
        </div>
        <button className="iconButton" onClick={() => navigator.clipboard.writeText(shareUrl)} title="Copy share URL">
          <Clipboard size={18} />
          <span>复制链接</span>
        </button>
      </header>

      <section className="scoreGrid">
        <div className={`scoreCard ${scoreTone(report.score)}`}>
          <span>总分</span>
          <strong>{report.score}</strong>
          <p>{report.score >= 80 ? '健康' : report.score >= 60 ? '可维护但有风险' : '需要优先治理'}</p>
        </div>
        <ScoreRadar breakdown={radar} />
      </section>

      <section className="metricGrid">
        <div><span>代码行数</span><strong>{report.static_analysis.total_code_lines.toLocaleString()}</strong></div>
        <div><span>文件数</span><strong>{report.static_analysis.source_file_count.toLocaleString()}</strong></div>
        <div><span>依赖</span><strong>{report.dependencies.dependency_count}</strong></div>
        <div><span>CVE</span><strong>{report.dependencies.vulnerabilities.length}</strong></div>
      </section>

      <DetailSection title="分项评分" defaultOpen>
        <div className="breakdown">
          {Object.entries(report.score_breakdown).map(([name, score]) => (
            <div key={name}><span>{name}</span><meter min="0" max="100" value={score} /><strong>{score}</strong></div>
          ))}
        </div>
      </DetailSection>

      <DetailSection title="圈复杂度 Top 10" defaultOpen>
        <table>
          <thead><tr><th>函数</th><th>文件</th><th>行</th><th>复杂度</th></tr></thead>
          <tbody>
            {report.static_analysis.top_complexity_functions.map((item, index) => (
              <tr key={`${item.path}-${item.line}-${index}`}>
                <td>{item.name}</td><td>{item.path}</td><td>{item.line}</td><td>{item.complexity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DetailSection>

      <DetailSection title="Commit 频率热力图" defaultOpen>
        <CommitHeatmap weeks={report.git_history.weekly_heatmap} />
      </DetailSection>

      <DetailSection title="高风险文件">
        <table>
          <thead><tr><th>文件</th><th>改动</th><th>大小</th></tr></thead>
          <tbody>
            {report.git_history.high_risk_files.map((item) => (
              <tr key={item.path}><td>{item.path}</td><td>{item.changes}</td><td>{Math.round(item.size_bytes / 1024)} KB</td></tr>
            ))}
          </tbody>
        </table>
      </DetailSection>

      <DetailSection title="依赖漏洞">
        {report.dependencies.vulnerability_error && <div className="warning"><AlertTriangle size={18} />{report.dependencies.vulnerability_error}</div>}
        {report.dependencies.vulnerabilities.length === 0 ? (
          <div className="okLine"><CheckCircle2 size={18} />未发现已知漏洞</div>
        ) : (
          <table>
            <thead><tr><th>包</th><th>ID</th><th>等级</th><th>摘要</th></tr></thead>
            <tbody>
              {report.dependencies.vulnerabilities.map((item) => (
                <tr key={`${item.package}-${item.id}`}><td>{item.package}</td><td><a href={item.url}>{item.id}</a></td><td>{item.severity}</td><td>{item.summary}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </DetailSection>

      <DetailSection title="README 质量">
        <div className="readmeScore"><Activity size={18} />{report.readme_quality.method}: {report.readme_quality.score}/100</div>
        <pre>{JSON.stringify(report.readme_quality.checks, null, 2)}</pre>
      </DetailSection>
    </main>
  );
}

function App() {
  const [route, setRoute] = useState(() => window.location.pathname);
  const [jobId, setJobId] = useState('');

  function navigate(path) {
    window.history.pushState({}, '', path);
    setRoute(path);
  }

  useEffect(() => {
    const handler = () => setRoute(window.location.pathname);
    window.addEventListener('popstate', handler);
    return () => window.removeEventListener('popstate', handler);
  }, []);

  if (route.startsWith('/reports/')) {
    return <ResultPage reportId={route.split('/').pop()} />;
  }
  if (route.startsWith('/jobs/')) {
    const routeJobId = route.split('/').pop();
    return <ProgressPage jobId={jobId || routeJobId} onComplete={(reportId) => navigate(`/reports/${reportId}`)} />;
  }
  return (
    <Home
      onStart={(id, reportUrl) => {
        if (reportUrl) {
          navigate(reportUrl);
          return;
        }
        setJobId(id);
        navigate(`/jobs/${id}`);
      }}
    />
  );
}

createRoot(document.getElementById('root')).render(<App />);
