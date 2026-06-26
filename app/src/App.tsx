import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import DownloadPage from './pages/DownloadPage'
import ProcessPage from './pages/ProcessPage'
import AnalysisPage from './pages/AnalysisPage'
import DataExplorerPage from './pages/DataExplorerPage'
import PipelinePage from './pages/PipelinePage'
import ModelPage from './pages/ModelPage'
import DataFlowPage from './pages/DataFlowPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="download" element={<DownloadPage />} />
        <Route path="process" element={<ProcessPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="explorer" element={<DataExplorerPage />} />
        <Route path="pipeline" element={<PipelinePage />} />
        <Route path="model" element={<ModelPage />} />
        <Route path="data-flow" element={<DataFlowPage />} />
      </Route>
    </Routes>
  )
}

export default App