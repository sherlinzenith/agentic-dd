"use client";

import React, { useState, useEffect } from "react";
import {
  FileText,
  Search,
  Bot,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Upload,
  RefreshCw,
  Database,
  Layers,
  ArrowRight,
  ExternalLink,
  Table as TableIcon,
  Cpu,
  Eye,
  SlidersHorizontal,
  FileCheck,
  Play,
  AlertTriangle,
  Plus,
  Settings,
  ListTodo,
  CheckSquare,
  Building2,
  Calendar,
  Briefcase,
  Tag,
  Check,
  ChevronDown,
  MessageSquare,
  Send,
  Trash2,
  User,
  Download
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

export default function DueDiligenceApp() {
  const [activeTab, setActiveTab] = useState("overview");
  const [projectId, setProjectId] = useState("");

  // Projects & Scope States
  const [projectsList, setProjectsList] = useState([]);
  const [currentProject, setCurrentProject] = useState(null);
  const [projectWorkstreams, setProjectWorkstreams] = useState([]);
  const [projectScopes, setProjectScopes] = useState({});
  const [projectTasks, setProjectTasks] = useState([]);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [generatingTasks, setGeneratingTasks] = useState(false);

  // DD Chatbot States
  const [conversationsList, setConversationsList] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [activeConversationDetail, setActiveConversationDetail] = useState(null);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [loadingConversationDetail, setLoadingConversationDetail] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [sendingChat, setSendingChat] = useState(false);
  const [chatError, setChatError] = useState(null);

  // Final DD Report States
  const [reportData, setReportData] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [reportError, setReportError] = useState(null);
  const [reportFilter, setReportFilter] = useState("all");
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingJson, setDownloadingJson] = useState(false);

  // Project Modal State
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [projectModalMode, setProjectModalMode] = useState("create");
  const [projectForm, setProjectForm] = useState({
    name: "",
    target_company: "",
    deal_type: "Acquisition",
    industry: "",
    diligence_period: "",
    description: "",
    financial: true,
    legal: true,
  });
  const [savingProject, setSavingProject] = useState(false);
  const [projectFormError, setProjectFormError] = useState(null);

  // Scope Modal State
  const [scopeModalOpen, setScopeModalOpen] = useState(false);
  const [activeScopeWs, setActiveScopeWs] = useState("financial");
  const [scopeTopics, setScopeTopics] = useState({});
  const [scopeKeyQuestions, setScopeKeyQuestions] = useState("");
  const [scopeReviewAreas, setScopeReviewAreas] = useState("");
  const [savingScope, setSavingScope] = useState(false);

  // Data States
  const [documents, setDocuments] = useState([]);
  const [findings, setFindings] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [loadingFindings, setLoadingFindings] = useState(false);

  // Central Orchestrator State
  const [orchestratorRunning, setOrchestratorRunning] = useState(false);
  const [orchestratorResult, setOrchestratorResult] = useState(null);
  const [orchestratorError, setOrchestratorError] = useState(null);
  const [orchestratorObjective, setOrchestratorObjective] = useState("");


  // Search State
  const [searchQuery, setSearchQuery] = useState("revenue and gross profit FY 2025-26");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  // Agent Runner State
  const [workstream, setWorkstream] = useState("financial");
  const [objective, setObjective] = useState(
    "Verify the company's reported revenue and gross profit for FY 2025-26 from source documents. After retrieving the values, record your finding using the record_finding tool with risk level and evidence."
  );
  const [runningAgent, setRunningAgent] = useState(false);
  const [agentResult, setAgentResult] = useState(null);


  // Upload State
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);

  // Modal / Details State
  const [selectedDocTables, setSelectedDocTables] = useState(null);
  const [loadingTables, setLoadingTables] = useState(false);
  const [reviewModal, setReviewModal] = useState({ isOpen: false, findingId: null, action: "REQUEST_MORE_EVIDENCE" });
  const [reviewComment, setReviewComment] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);

  // Fetch Documents
  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const res = await fetch(`${API_BASE}/documents?project_id=${projectId}`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
      }
    } catch (err) {
      console.error("Error fetching documents:", err);
    } finally {
      setLoadingDocs(false);
    }
  };

  // Review & Reanalysis Tracking States
  const [reanalysisRuns, setReanalysisRuns] = useState([]);
  const [projectRequests, setProjectRequests] = useState([]);
  const [loadingReanalysis, setLoadingReanalysis] = useState(false);
  const [triggeringWorker, setTriggeringWorker] = useState(false);
  const [findingFilter, setFindingFilter] = useState("ALL");

  // Fetch Findings
  const fetchFindings = async () => {
    setLoadingFindings(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/findings`);
      if (res.ok) {
        const data = await res.json();
        setFindings(data.findings || []);
      }
    } catch (err) {
      console.error("Error fetching findings:", err);
    } finally {
      setLoadingFindings(false);
    }
  };

  // Fetch Reanalysis Runs
  const fetchReanalysis = async () => {
    setLoadingReanalysis(true);
    try {
      const res = await fetch(`${API_BASE}/reanalysis/project/${projectId}`);
      if (res.ok) {
        const data = await res.json();
        setReanalysisRuns(data || []);
      }
    } catch (err) {
      console.error("Error fetching reanalysis runs:", err);
    } finally {
      setLoadingReanalysis(false);
    }
  };

  // Fetch Requests
  const fetchRequests = async () => {
    try {
      const res = await fetch(`${API_BASE}/requests/project/${projectId}`);
      if (res.ok) {
        const data = await res.json();
        setProjectRequests(data || []);
      }
    } catch (err) {
      console.error("Error fetching project requests:", err);
    }
  };

  // Submit Human Review (APPROVE, REJECT, REQUEST_MORE_EVIDENCE)
  const submitReview = async (findingId, action, comment = null) => {
    setSubmittingReview(true);
    try {
      const res = await fetch(`${API_BASE}/findings/${findingId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: action,
          reviewer: "Human Reviewer",
          comment: comment,
        }),
      });
      if (res.ok) {
        setReviewModal({ isOpen: false, findingId: null, action: "REQUEST_MORE_EVIDENCE" });
        setReviewComment("");
        await fetchFindings();
        await fetchReanalysis();
        await fetchRequests();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(`Review action failed: ${errData.detail || res.statusText}`);
      }
    } catch (err) {
      console.error("Error submitting review:", err);
      alert(`Network error submitting review: ${err.message}`);
    } finally {
      setSubmittingReview(false);
    }
  };

  // Trigger Reanalysis Worker on Demand
  const handleTriggerWorker = async () => {
    setTriggeringWorker(true);
    try {
      const res = await fetch(`${API_BASE}/reanalysis/process-next`, {
        method: "POST",
      });
      if (res.ok) {
        await fetchReanalysis();
        await fetchFindings();
        await fetchRequests();
      }
    } catch (err) {
      console.error("Error running reanalysis worker:", err);
    } finally {
      setTriggeringWorker(false);
    }
  };

  // Project, Scope & Task API Handlers
  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      if (res.ok) {
        const data = await res.json();
        const list = data.projects || [];
        setProjectsList(list);
        if (list.length > 0) {
          setProjectId(prev => {
            if (!prev || !list.some(p => p.id === prev)) {
              return list[0].id;
            }
            return prev;
          });
        }
      }
    } catch (err) {
      console.error("Error fetching projects:", err);
    }
  };

  const fetchProjectDetails = async (idToFetch = projectId) => {
    if (!idToFetch) return;
    try {
      const res = await fetch(`${API_BASE}/projects/${idToFetch}/summary`);
      if (res.ok) {
        const data = await res.json();
        setCurrentProject(data.project || null);
        setProjectWorkstreams(data.workstreams || []);
        setProjectScopes(data.scopes || {});
      } else {
        const pRes = await fetch(`${API_BASE}/projects/${idToFetch}`);
        if (pRes.ok) {
          const pData = await pRes.json();
          setCurrentProject(pData.project || null);
          setProjectWorkstreams(pData.workstreams || []);
        }
      }
    } catch (err) {
      console.error("Error fetching project details:", err);
    }
  };

  const fetchScopes = async (idToFetch = projectId) => {
    if (!idToFetch) return;
    try {
      const res = await fetch(`${API_BASE}/projects/${idToFetch}/scopes`);
      if (res.ok) {
        const data = await res.json();
        setProjectScopes(data.scopes || {});
      }
    } catch (err) {
      console.error("Error fetching scopes:", err);
    }
  };

  const fetchTasks = async (idToFetch = projectId) => {
    if (!idToFetch) return;
    setLoadingTasks(true);
    try {
      const res = await fetch(`${API_BASE}/tasks/project/${idToFetch}`);
      if (res.ok) {
        const data = await res.json();
        setProjectTasks(data || []);
      }
    } catch (err) {
      console.error("Error fetching tasks:", err);
    } finally {
      setLoadingTasks(false);
    }
  };

  const openCreateProjectModal = () => {
    setProjectModalMode("create");
    setProjectForm({
      name: "",
      target_company: "",
      deal_type: "Acquisition",
      industry: "",
      diligence_period: "Q1 2026",
      description: "",
      financial: true,
      legal: true,
    });
    setProjectFormError(null);
    setProjectModalOpen(true);
  };

  const openEditProjectModal = () => {
    if (!currentProject) return;
    setProjectModalMode("edit");
    const finEnabled = projectWorkstreams.find(w => w.name === "financial")?.enabled ?? true;
    const legEnabled = projectWorkstreams.find(w => w.name === "legal")?.enabled ?? true;
    setProjectForm({
      name: currentProject.name || "",
      target_company: currentProject.target_company || "",
      deal_type: currentProject.deal_type || "Acquisition",
      industry: currentProject.industry || "",
      diligence_period: currentProject.diligence_period || "",
      description: currentProject.description || "",
      financial: finEnabled,
      legal: legEnabled,
    });
    setProjectFormError(null);
    setProjectModalOpen(true);
  };

  const handleSaveProject = async (e) => {
    if (e) e.preventDefault();
    if (!projectForm.name.trim() || !projectForm.target_company.trim()) {
      setProjectFormError("Project Name and Target Company are required.");
      return;
    }
    setSavingProject(true);
    setProjectFormError(null);
    try {
      const enabledWs = [];
      if (projectForm.financial) enabledWs.push("financial");
      if (projectForm.legal) enabledWs.push("legal");

      if (projectModalMode === "create") {
        const res = await fetch(`${API_BASE}/projects`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: projectForm.name,
            target_company: projectForm.target_company,
            deal_type: projectForm.deal_type,
            industry: projectForm.industry,
            diligence_period: projectForm.diligence_period,
            description: projectForm.description,
            enabled_workstreams: enabledWs,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          const newId = data.project.id;
          setProjectModalOpen(false);
          await fetchProjects();
          setProjectId(newId);
        } else {
          const errData = await res.json().catch(() => ({}));
          setProjectFormError(errData.detail || "Failed to create project");
        }
      } else {
        const res = await fetch(`${API_BASE}/projects/${projectId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: projectForm.name,
            target_company: projectForm.target_company,
            deal_type: projectForm.deal_type,
            industry: projectForm.industry,
            diligence_period: projectForm.diligence_period,
            description: projectForm.description,
          }),
        });
        await fetch(`${API_BASE}/projects/${projectId}/workstreams`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            workstreams: [
              { name: "financial", enabled: projectForm.financial },
              { name: "legal", enabled: projectForm.legal },
            ],
          }),
        });
        setProjectModalOpen(false);
        fetchProjects();
        fetchProjectDetails(projectId);
      }
    } catch (err) {
      setProjectFormError(err.message);
    } finally {
      setSavingProject(false);
    }
  };

  const openScopeModal = (wsName) => {
    setActiveScopeWs(wsName);
    const existingScope = projectScopes[wsName] || {};
    const keyQs = Array.isArray(existingScope.key_questions)
      ? existingScope.key_questions.join("\n")
      : "";
    const revAreas = Array.isArray(existingScope.requested_review_areas)
      ? existingScope.requested_review_areas.join("\n")
      : "";

    // Copy topics excluding special array keys
    const topicsObj = {};
    Object.keys(existingScope).forEach(k => {
      if (k !== "key_questions" && k !== "requested_review_areas") {
        topicsObj[k] = existingScope[k];
      }
    });

    setScopeTopics(topicsObj);
    setScopeKeyQuestions(keyQs);
    setScopeReviewAreas(revAreas);
    setScopeModalOpen(true);
  };

  const handleSaveScope = async () => {
    setSavingScope(true);
    try {
      const qList = scopeKeyQuestions.split("\n").map(q => q.trim()).filter(Boolean);
      const aList = scopeReviewAreas.split("\n").map(a => a.trim()).filter(Boolean);
      const payloadScope = {
        ...scopeTopics,
        key_questions: qList,
        requested_review_areas: aList,
      };

      const res = await fetch(`${API_BASE}/projects/${projectId}/scope`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workstream: activeScopeWs,
          scope: payloadScope,
        }),
      });
      if (res.ok) {
        setScopeModalOpen(false);
        fetchScopes();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(`Failed to save scope: ${errData.detail || res.statusText}`);
      }
    } catch (err) {
      console.error("Error saving scope:", err);
      alert(`Network error saving scope: ${err.message}`);
    } finally {
      setSavingScope(false);
    }
  };

  const handleGeneratePlanTasks = async () => {
    setGeneratingTasks(true);
    try {
      const enabledWs = projectWorkstreams.filter(w => w.enabled).map(w => w.name);
      const res = await fetch(`${API_BASE}/tasks/project/${projectId}/generate-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled_workstreams: enabledWs.length > 0 ? enabledWs : ["financial", "legal"],
        }),
      });
      if (res.ok) {
        await fetchTasks();
      }
    } catch (err) {
      console.error("Error generating tasks:", err);
    } finally {
      setGeneratingTasks(false);
    }
  };

  const handleUpdateTaskStatus = async (taskId, newStatus) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        fetchTasks();
      }
    } catch (err) {
      console.error("Error updating task status:", err);
    }
  };

  // Chat API Handlers
  const fetchConversations = async (projId = projectId) => {
    if (!projId) return;
    setLoadingConversations(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${projId}/chat/conversations`);
      if (res.ok) {
        const data = await res.json();
        setConversationsList(data || []);
        if (data && data.length > 0 && !activeConversationId) {
          setActiveConversationId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Error fetching conversations:", err);
    } finally {
      setLoadingConversations(false);
    }
  };

  const fetchConversationDetail = async (projId = projectId, convId = activeConversationId) => {
    if (!projId || !convId) return;
    setLoadingConversationDetail(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${projId}/chat/conversations/${convId}`);
      if (res.ok) {
        const data = await res.json();
        setActiveConversationDetail(data);
      }
    } catch (err) {
      console.error("Error fetching conversation details:", err);
    } finally {
      setLoadingConversationDetail(false);
    }
  };

  const handleCreateNewConversation = async (title = "New Due Diligence Chat") => {
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/chat/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (res.ok) {
        const data = await res.json();
        await fetchConversations(projectId);
        setActiveConversationId(data.id);
        setActiveConversationDetail({
          ...data,
          messages: [],
        });
      }
    } catch (err) {
      console.error("Error creating conversation:", err);
    }
  };

  const handleDeleteConversation = async (convId, e) => {
    if (e) e.stopPropagation();
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/chat/conversations/${convId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        if (activeConversationId === convId) {
          setActiveConversationId(null);
          setActiveConversationDetail(null);
        }
        await fetchConversations(projectId);
      }
    } catch (err) {
      console.error("Error deleting conversation:", err);
    }
  };

  const handleSendChatMessage = async (e, customPrompt = null) => {
    if (e) e.preventDefault();
    const textToSend = (customPrompt || chatInput).trim();
    if (!textToSend || sendingChat) return;

    setSendingChat(true);
    setChatError(null);
    setChatInput("");

    let convId = activeConversationId;
    try {
      if (!convId) {
        const createRes = await fetch(`${API_BASE}/projects/${projectId}/chat/conversations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: textToSend.slice(0, 40) }),
        });
        if (createRes.ok) {
          const createData = await createRes.json();
          convId = createData.id;
          setActiveConversationId(convId);
        } else {
          throw new Error("Failed to initialize conversation.");
        }
      }

      const optimisticUserMsg = {
        id: "temp-" + Date.now(),
        conversation_id: convId,
        role: "user",
        content: textToSend,
        sources: [],
        is_insufficient_evidence: false,
        created_at: new Date().toISOString(),
      };

      setActiveConversationDetail((prev) => ({
        ...prev,
        messages: [...(prev?.messages || []), optimisticUserMsg],
      }));

      const res = await fetch(`${API_BASE}/projects/${projectId}/chat/conversations/${convId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: textToSend }),
      });

      if (res.ok) {
        await fetchConversationDetail(projectId, convId);
        await fetchConversations(projectId);
      } else {
        const errData = await res.json().catch(() => ({}));
        setChatError(errData.detail || "Error generating response from local model.");
        await fetchConversationDetail(projectId, convId);
      }
    } catch (err) {
      console.error("Error sending chat message:", err);
      setChatError(err.message || "Failed to communicate with DD chatbot.");
    } finally {
      setSendingChat(false);
    }
  };

  const fetchReportPreview = async (pId = projectId) => {
    if (!pId) return;
    setLoadingReport(true);
    setReportError(null);
    try {
      const res = await fetch(`${API_BASE}/projects/${pId}/reports/preview`);
      if (res.ok) {
        const data = await res.json();
        setReportData(data);
      } else {
        const err = await res.json().catch(() => ({}));
        setReportError(err.detail || "Failed to compile report preview");
      }
    } catch (err) {
      setReportError(err.message || "Network error loading report preview");
    } finally {
      setLoadingReport(false);
    }
  };

  const handleDownloadPdf = async (pId = projectId) => {
    if (!pId || downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${pId}/reports/export/pdf`);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const targetName = reportData?.metadata?.target_company ? reportData.metadata.target_company.replace(/[^a-zA-Z0-9_-]/g, "_") : "dd";
        a.download = `${targetName}_Due_Diligence_Report.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        alert("Failed to download PDF report.");
      }
    } catch (err) {
      alert("Error downloading PDF: " + err.message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadJson = async (pId = projectId) => {
    if (!pId || downloadingJson) return;
    setDownloadingJson(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${pId}/reports/export/json`);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const targetName = reportData?.metadata?.target_company ? reportData.metadata.target_company.replace(/[^a-zA-Z0-9_-]/g, "_") : "dd";
        a.download = `${targetName}_Due_Diligence_Report.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        alert("Failed to download JSON report.");
      }
    } catch (err) {
      alert("Error downloading JSON: " + err.message);
    } finally {
      setDownloadingJson(false);
    }
  };

  useEffect(() => {
    if (activeTab === "report" && projectId) {
      fetchReportPreview(projectId);
    }
  }, [activeTab, projectId]);

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (projectId) {
      fetchProjectDetails(projectId);
      fetchScopes(projectId);
      fetchTasks(projectId);
      fetchDocuments();
      fetchFindings();
      fetchReanalysis();
      fetchRequests();
      fetchConversations(projectId);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId && activeConversationId) {
      fetchConversationDetail(projectId, activeConversationId);
    }
  }, [activeConversationId]);

  // Semantic Search
  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`${API_BASE}/documents/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: searchQuery,
          project_id: projectId,
          limit: 5,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setSearching(false);
    }
  };

  // Run Agent
  const handleRunAgent = async () => {
    setRunningAgent(true);
    setAgentResult(null);
    try {
      const res = await fetch(`${API_BASE}/documents/run-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          workstream: workstream,
          objective: objective,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setAgentResult(data);
        fetchFindings();
      }
    } catch (err) {
      console.error("Agent run failed:", err);
    } finally {
      setRunningAgent(false);
    }
  };

  // Central Orchestrator Workflow
  const handleRunFullDD = async () => {
    if (!projectId.trim()) return;
    setOrchestratorRunning(true);
    setOrchestratorError(null);
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/run-full-dd`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          objective: orchestratorObjective.trim() || undefined,
          max_agent_iterations: 5,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setOrchestratorResult(data);
        fetchDocuments();
        fetchFindings();
      } else {
        const err = await res.json();
        setOrchestratorError(err.detail || "Central Due Diligence run failed");
      }
    } catch (err) {
      setOrchestratorError(err.message);
    } finally {
      setOrchestratorRunning(false);
    }
  };

  const handleFetchOrchestratorStatus = async () => {
    if (!projectId.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/orchestrator/status`);
      if (res.ok) {
        const data = await res.json();
        if (data.status) {
          setOrchestratorResult({
            overall_status: data.status.overall_status,
            investigation_id: data.status.investigation_id,
            project_id: data.status.project_id,
            stages: data.status.stages || {},
            stage_errors: data.status.stage_errors || [],
            findings_count: data.status.findings_count || 0,
          });
        }
      } else {
        const err = await res.json();
        setOrchestratorError(err.detail || "No orchestration status available");
      }
    } catch (err) {
      setOrchestratorError(err.message);
    }
  };

  // Upload Document
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    setUploading(true);
    setUploadMessage("Processing document with Docling OCR & Qwen3 classification...");
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("project_id", projectId);

    try {
      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setUploadMessage(`Success! Ingested ${selectedFile.name} as ${data.document?.category || 'document'}`);
        setSelectedFile(null);
        fetchDocuments();
      } else {
        const err = await res.json();
        setUploadMessage(`Upload failed: ${err.detail || "Server error"}`);
      }
    } catch (err) {
      setUploadMessage(`Error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  // View Tables
  const viewTables = async (docId) => {
    setLoadingTables(true);
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}/tables`);
      if (res.ok) {
        const data = await res.json();
        setSelectedDocTables(data.tables || []);
      }
    } catch (err) {
      console.error("Failed to load tables:", err);
    } finally {
      setLoadingTables(false);
    }
  };



  const totalChunks = documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
  const totalTables = documents.reduce((acc, d) => acc + (d.table_count || 0), 0);
  const pendingReviewCount = findings.filter(f => f.status === "REVIEW_REQUIRED").length;

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Top Header */}
      <header className="app-header">
        <div className="header-inner">
          <div className="logo-group">
            <div className="logo-badge">DD</div>
            <div className="logo-text">
              <h1>Agentic AI Due Diligence</h1>
              <p>Autonomous Multi-Agent Investigation Platform</p>
            </div>
          </div>

          <div className="header-status-pills">
            <div className="status-pill">
              <span className="pulse-dot"></span>
              <span>pgvector : 5432</span>
            </div>
            <div className="status-pill">
              <Cpu size={13} color="#6366f1" />
              <span>Ollama Qwen3 : 11434</span>
            </div>
            <div className="status-pill">
              <Layers size={13} color="#06b6d4" />
              <span>BGE-M3 (1024-d)</span>
            </div>
            <div className="status-pill" style={{ borderColor: "rgba(99, 102, 241, 0.4)", color: "#a5b4fc", display: "flex", alignItems: "center", gap: "8px", padding: "4px 10px" }}>
              <Briefcase size={13} color="#818cf8" />
              <strong>Project:</strong>
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                style={{
                  background: "#0f172a",
                  border: "1px solid rgba(99, 102, 241, 0.3)",
                  borderRadius: "6px",
                  color: "#f8fafc",
                  fontSize: "12px",
                  fontWeight: "600",
                  padding: "2px 6px",
                  outline: "none",
                  cursor: "pointer"
                }}
              >
                {projectsList.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name || p.id} ({p.id})
                  </option>
                ))}
                {!projectsList.some((p) => p.id === projectId) && (
                  <option value={projectId}>{projectId}</option>
                )}
              </select>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={openCreateProjectModal}
                title="Create New Project"
                style={{ padding: "2px 6px", fontSize: "11px", display: "flex", alignItems: "center", gap: "3px" }}
              >
                <Plus size={11} /> New
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={openEditProjectModal}
                title="Edit Project Configuration"
                style={{ padding: "2px 6px", fontSize: "11px", display: "flex", alignItems: "center", gap: "3px" }}
              >
                <Settings size={11} /> Edit
              </button>
            </div>
            {currentProject?.target_company && (
              <div className="status-pill" style={{ borderColor: "rgba(16, 185, 129, 0.3)", color: "#34d399", display: "flex", alignItems: "center", gap: "6px" }}>
                <Building2 size={13} />
                <span>Target: <strong>{currentProject.target_company}</strong></span>
                {currentProject.deal_type && <span style={{ opacity: 0.7 }}>({currentProject.deal_type})</span>}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="app-container">
        {/* Navigation Tabs */}
        <nav className="nav-tabs">
          <button
            className={`nav-tab-btn ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            <SlidersHorizontal size={16} /> Overview
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "documents" ? "active" : ""}`}
            onClick={() => setActiveTab("documents")}
          >
            <FileText size={16} /> Documents & Ingestion ({documents.length})
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "search" ? "active" : ""}`}
            onClick={() => setActiveTab("search")}
          >
            <Search size={16} /> Knowledge Base Search
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "agents" ? "active" : ""}`}
            onClick={() => setActiveTab("agents")}
          >
            <Bot size={16} /> Agent Investigation Lab
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "findings" ? "active" : ""}`}
            onClick={() => setActiveTab("findings")}
          >
            <ShieldAlert size={16} /> Findings & Review ({findings.length})
            {pendingReviewCount > 0 && (
              <span style={{ background: "#f59e0b", color: "#000", padding: "1px 6px", borderRadius: "10px", fontSize: "11px", fontWeight: "bold" }}>
                {pendingReviewCount}
              </span>
            )}
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "chat" ? "active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            <MessageSquare size={16} /> DD Chatbot & Evidence QA
          </button>
          <button
            className={`nav-tab-btn ${activeTab === "report" ? "active" : ""}`}
            onClick={() => setActiveTab("report")}
          >
            <FileText size={16} /> Final DD Report & Export
          </button>
        </nav>

        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div>
            {/* Target Profile & Investigation Scope Card */}
            <div className="glass-card" style={{ marginBottom: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px", marginBottom: "16px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                    <div style={{ background: "rgba(16, 185, 129, 0.2)", padding: "6px", borderRadius: "8px", color: "#34d399" }}>
                      <Building2 size={18} />
                    </div>
                    <h2 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>
                      {currentProject?.target_company ? `${currentProject.target_company} — Target Profile & Scope` : "Target Profile & Scope"}
                    </h2>
                  </div>
                  <p style={{ fontSize: "13px", color: "#94a3b8", maxWidth: "700px" }}>
                    {currentProject?.description || "Due diligence investigation parameters, workstream configuration, and key investigative questions."}
                  </p>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={openEditProjectModal}
                  >
                    <Settings size={14} /> Edit Target & Workstreams
                  </button>
                </div>
              </div>

              {/* Company Info Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px", marginBottom: "18px" }}>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px 14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "600", textTransform: "uppercase" }}>Target Company</div>
                  <div style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc", marginTop: "4px" }}>
                    {currentProject?.target_company || "Not Configured"}
                  </div>
                </div>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px 14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "600", textTransform: "uppercase" }}>Deal Type</div>
                  <div style={{ fontSize: "15px", fontWeight: "700", color: "#818cf8", marginTop: "4px" }}>
                    {currentProject?.deal_type || "Acquisition"}
                  </div>
                </div>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px 14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "600", textTransform: "uppercase" }}>Industry Sector</div>
                  <div style={{ fontSize: "15px", fontWeight: "700", color: "#38bdf8", marginTop: "4px" }}>
                    {currentProject?.industry || "Technology"}
                  </div>
                </div>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px 14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "600", textTransform: "uppercase" }}>Diligence Period</div>
                  <div style={{ fontSize: "15px", fontWeight: "700", color: "#fbbf24", marginTop: "4px" }}>
                    {currentProject?.diligence_period || "Q1 2026"}
                  </div>
                </div>
              </div>

              {/* Workstreams & Scope Review Areas */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
                {/* Financial Workstream Box */}
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "14px 16px", borderRadius: "10px", border: "1px solid rgba(52, 211, 153, 0.2)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span className="badge badge-financial" style={{ fontSize: "11px" }}>Financial DD</span>
                      <span className={`badge ${projectWorkstreams.find(w => w.name === "financial")?.enabled !== false ? "badge-verified" : "badge-medium"}`} style={{ fontSize: "10px" }}>
                        {projectWorkstreams.find(w => w.name === "financial")?.enabled !== false ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => openScopeModal("financial")}
                      style={{ padding: "3px 8px", fontSize: "11px" }}
                    >
                      Configure Scope
                    </button>
                  </div>
                  <div style={{ fontSize: "12px", color: "#cbd5e1", marginBottom: "6px" }}>
                    <strong>Key Questions ({projectScopes?.financial?.key_questions?.length || 0}):</strong>
                  </div>
                  <ul style={{ fontSize: "11.5px", color: "#94a3b8", paddingLeft: "16px", margin: 0, maxHeight: "85px", overflowY: "auto" }}>
                    {(projectScopes?.financial?.key_questions && projectScopes.financial.key_questions.length > 0) ? (
                      projectScopes.financial.key_questions.map((q, idx) => <li key={idx} style={{ marginBottom: "2px" }}>{q}</li>)
                    ) : (
                      <li style={{ color: "#64748b", fontStyle: "italic" }}>Default financial checks (revenue, EBITDA, debt covenants, quality of earnings)</li>
                    )}
                  </ul>
                </div>

                {/* Legal Workstream Box */}
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "14px 16px", borderRadius: "10px", border: "1px solid rgba(56, 189, 248, 0.2)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span className="badge badge-legal" style={{ fontSize: "11px" }}>Legal DD</span>
                      <span className={`badge ${projectWorkstreams.find(w => w.name === "legal")?.enabled !== false ? "badge-verified" : "badge-medium"}`} style={{ fontSize: "10px" }}>
                        {projectWorkstreams.find(w => w.name === "legal")?.enabled !== false ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => openScopeModal("legal")}
                      style={{ padding: "3px 8px", fontSize: "11px" }}
                    >
                      Configure Scope
                    </button>
                  </div>
                  <div style={{ fontSize: "12px", color: "#cbd5e1", marginBottom: "6px" }}>
                    <strong>Key Questions ({projectScopes?.legal?.key_questions?.length || 0}):</strong>
                  </div>
                  <ul style={{ fontSize: "11.5px", color: "#94a3b8", paddingLeft: "16px", margin: 0, maxHeight: "85px", overflowY: "auto" }}>
                    {(projectScopes?.legal?.key_questions && projectScopes.legal.key_questions.length > 0) ? (
                      projectScopes.legal.key_questions.map((q, idx) => <li key={idx} style={{ marginBottom: "2px" }}>{q}</li>)
                    ) : (
                      <li style={{ color: "#64748b", fontStyle: "italic" }}>Default legal checks (change of control, regulatory compliance, liabilities, litigation)</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>

            {/* Central Orchestrator Action Card */}
            <div className="glass-card" style={{ marginBottom: "28px", border: "1px solid rgba(99, 102, 241, 0.3)", background: "linear-gradient(180deg, rgba(16, 23, 38, 0.9) 0%, rgba(10, 14, 26, 0.8) 100%)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px", marginBottom: "16px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                    <div style={{ background: "rgba(99, 102, 241, 0.2)", padding: "6px", borderRadius: "8px", color: "#818cf8" }}>
                      <Play size={18} />
                    </div>
                    <h2 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>
                      Central Due Diligence Orchestrator
                    </h2>
                  </div>
                  <p style={{ fontSize: "13px", color: "#94a3b8", maxWidth: "680px" }}>
                    Autonomous investigation pipeline: <strong>Planner</strong> → <strong>Financial Agent</strong> + <strong>Legal Agent</strong> → <strong>Cross-Domain Agent</strong> → <strong>Evidence Validation</strong>.
                  </p>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    className="btn btn-secondary"
                    onClick={handleFetchOrchestratorStatus}
                    disabled={orchestratorRunning}
                  >
                    <RefreshCw size={14} /> Refresh Workflow Status
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={handleRunFullDD}
                    disabled={orchestratorRunning}
                    style={{ padding: "10px 20px", fontWeight: "700" }}
                  >
                    {orchestratorRunning ? <RefreshCw className="animate-spin" size={16} /> : <Play size={16} />}
                    {orchestratorRunning ? "Orchestrating Full DD..." : "Run Full Due Diligence"}
                  </button>
                </div>
              </div>

              {/* Optional Objective Input */}
              <div style={{ display: "flex", gap: "12px", alignItems: "center", marginTop: "12px" }}>
                <input
                  type="text"
                  placeholder="Optional custom DD objective (e.g., Focus on revenue concentration, debt covenants, and change of control risks)..."
                  value={orchestratorObjective}
                  onChange={(e) => setOrchestratorObjective(e.target.value)}
                  className="input-field"
                  style={{ flex: 1, fontSize: "13px" }}
                />
              </div>

              {/* Running Status Banner */}
              {orchestratorRunning && (
                <div style={{ marginTop: "16px", padding: "14px 18px", borderRadius: "10px", background: "rgba(99, 102, 241, 0.12)", border: "1px solid rgba(99, 102, 241, 0.3)", display: "flex", alignItems: "center", gap: "12px" }}>
                  <RefreshCw className="animate-spin" size={20} color="#818cf8" />
                  <div>
                    <div style={{ fontSize: "14px", fontWeight: "700", color: "#c7d2fe" }}>
                      Investigation Workflow in Progress
                    </div>
                    <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "2px" }}>
                      Executing Planner → Financial Agent → Legal Agent → Cross-Domain Agent → Evidence Validation...
                    </div>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {orchestratorError && (
                <div style={{ marginTop: "16px", padding: "12px 16px", borderRadius: "8px", background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#fca5a5", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <AlertTriangle size={16} />
                  <span>{orchestratorError}</span>
                </div>
              )}

              {/* Orchestrator Result Details */}
              {orchestratorResult && !orchestratorRunning && (
                <div style={{ marginTop: "20px", paddingTop: "18px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <span style={{ fontSize: "13px", fontWeight: "600", color: "#94a3b8" }}>OVERALL STATUS:</span>
                      <span
                        className={`badge ${
                          orchestratorResult.overall_status === "COMPLETED"
                            ? "badge-verified"
                            : orchestratorResult.overall_status === "PARTIAL_FAILURE"
                            ? "badge-medium"
                            : "badge-high"
                        }`}
                        style={{ fontSize: "12px", padding: "4px 10px" }}
                      >
                        {orchestratorResult.overall_status || "UNKNOWN"}
                      </span>
                      {orchestratorResult.investigation_id && (
                        <span style={{ fontSize: "12px", color: "#64748b" }}>
                          ID: {orchestratorResult.investigation_id.slice(0, 8)}...
                        </span>
                      )}
                    </div>
                    {orchestratorResult.findings_count !== undefined && (
                      <span style={{ fontSize: "13px", color: "#e2e8f0" }}>
                        Total Findings: <strong>{orchestratorResult.findings_count}</strong>
                      </span>
                    )}
                  </div>

                  {/* Stage Grid */}
                  {orchestratorResult.stages && (
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "12px" }}>
                      {/* 1. Planner */}
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <span style={{ fontSize: "12px", fontWeight: "700", color: "#818cf8" }}>1. PLANNER</span>
                          <span className={`badge ${orchestratorResult.stages.planner?.status === "SUCCESS" ? "badge-verified" : "badge-medium"}`} style={{ fontSize: "10px" }}>
                            {orchestratorResult.stages.planner?.status || "PENDING"}
                          </span>
                        </div>
                        <p style={{ fontSize: "11px", color: "#94a3b8" }}>
                          {orchestratorResult.stages.planner?.plan_summary || "Investigation plan formulated."}
                        </p>
                      </div>

                      {/* 2. Financial */}
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <span style={{ fontSize: "12px", fontWeight: "700", color: "#34d399" }}>2. FINANCIAL AGENT</span>
                          <span className={`badge ${orchestratorResult.stages.financial?.status === "SUCCESS" ? "badge-verified" : orchestratorResult.stages.financial?.status === "SKIPPED" ? "" : "badge-high"}`} style={{ fontSize: "10px" }}>
                            {orchestratorResult.stages.financial?.status || "PENDING"}
                          </span>
                        </div>
                        <p style={{ fontSize: "11px", color: "#94a3b8" }}>
                          {orchestratorResult.stages.financial?.status === "SKIPPED"
                            ? orchestratorResult.stages.financial.reason
                            : `Tools called: ${orchestratorResult.stages.financial?.tool_calls || 0} (${orchestratorResult.stages.financial?.iterations || 0} steps)`}
                        </p>
                      </div>

                      {/* 3. Legal */}
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <span style={{ fontSize: "12px", fontWeight: "700", color: "#38bdf8" }}>3. LEGAL AGENT</span>
                          <span className={`badge ${orchestratorResult.stages.legal?.status === "SUCCESS" ? "badge-verified" : orchestratorResult.stages.legal?.status === "SKIPPED" ? "" : "badge-high"}`} style={{ fontSize: "10px" }}>
                            {orchestratorResult.stages.legal?.status || "PENDING"}
                          </span>
                        </div>
                        <p style={{ fontSize: "11px", color: "#94a3b8" }}>
                          {orchestratorResult.stages.legal?.status === "SKIPPED"
                            ? orchestratorResult.stages.legal.reason
                            : `Tools called: ${orchestratorResult.stages.legal?.tool_calls || 0} (${orchestratorResult.stages.legal?.iterations || 0} steps)`}
                        </p>
                      </div>

                      {/* 4. Cross-Domain */}
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <span style={{ fontSize: "12px", fontWeight: "700", color: "#f472b6" }}>4. CROSS-DOMAIN</span>
                          <span className={`badge ${orchestratorResult.stages.cross_domain?.status === "SUCCESS" ? "badge-verified" : orchestratorResult.stages.cross_domain?.status === "SKIPPED" ? "" : "badge-high"}`} style={{ fontSize: "10px" }}>
                            {orchestratorResult.stages.cross_domain?.status || "PENDING"}
                          </span>
                        </div>
                        <p style={{ fontSize: "11px", color: "#94a3b8" }}>
                          {orchestratorResult.stages.cross_domain?.status === "SKIPPED"
                            ? orchestratorResult.stages.cross_domain.reason
                            : `Tools called: ${orchestratorResult.stages.cross_domain?.tool_calls || 0} (${orchestratorResult.stages.cross_domain?.iterations || 0} steps)`}
                        </p>
                      </div>

                      {/* 5. Evidence Validation */}
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.05)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <span style={{ fontSize: "12px", fontWeight: "700", color: "#fbbf24" }}>5. EVIDENCE VALIDATION</span>
                          <span className={`badge ${orchestratorResult.stages.evidence_validation?.status === "SUCCESS" ? "badge-verified" : "badge-high"}`} style={{ fontSize: "10px" }}>
                            {orchestratorResult.stages.evidence_validation?.status || "PENDING"}
                          </span>
                        </div>
                        <p style={{ fontSize: "11px", color: "#94a3b8" }}>
                          Verified: <strong>{orchestratorResult.stages.evidence_validation?.verified_count || 0}</strong> / Total: {orchestratorResult.stages.evidence_validation?.total_evidence || 0}
                          {orchestratorResult.stages.evidence_validation?.discrepancy_count > 0 && ` • Discrepancies: ${orchestratorResult.stages.evidence_validation.discrepancy_count}`}
                          {orchestratorResult.stages.evidence_validation?.duplicates_cleaned > 0 && ` • Cleaned ${orchestratorResult.stages.evidence_validation.duplicates_cleaned} dups`}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Stage Errors */}
                  {orchestratorResult.stage_errors && orchestratorResult.stage_errors.length > 0 && (
                    <div style={{ marginTop: "14px", padding: "10px 14px", borderRadius: "8px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", fontSize: "12px", color: "#fca5a5" }}>
                      <strong>Workflow Warnings/Errors:</strong>
                      <ul style={{ paddingLeft: "18px", marginTop: "4px" }}>
                        {orchestratorResult.stage_errors.map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Investigation Plan & Real DDTasks Card */}
            <div className="glass-card" style={{ marginBottom: "28px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "14px", marginBottom: "16px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                    <div style={{ background: "rgba(99, 102, 241, 0.2)", padding: "6px", borderRadius: "8px", color: "#818cf8" }}>
                      <ListTodo size={18} />
                    </div>
                    <h3 style={{ fontSize: "17px", fontWeight: "700", color: "#f8fafc" }}>
                      Investigation Plan & Real DD Tasks
                    </h3>
                    <span className="badge badge-verified" style={{ fontSize: "11px" }}>
                      {projectTasks.filter(t => t.status === "DONE").length} / {projectTasks.length} Completed
                    </span>
                  </div>
                  <p style={{ fontSize: "12.5px", color: "#94a3b8" }}>
                    Real task entities persisted in PostgreSQL (<code>DDTask</code>). Workstream tasks automatically progress during pipeline execution.
                  </p>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => fetchTasks(projectId)}
                    disabled={loadingTasks}
                  >
                    <RefreshCw className={loadingTasks ? "animate-spin" : ""} size={13} /> Refresh Tasks
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleGeneratePlanTasks}
                    disabled={generatingTasks}
                  >
                    {generatingTasks ? <RefreshCw className="animate-spin" size={13} /> : <CheckSquare size={13} />}
                    {generatingTasks ? "Generating..." : "Generate Plan Tasks"}
                  </button>
                </div>
              </div>

              {projectTasks.length === 0 ? (
                <div style={{ padding: "28px", textAlign: "center", background: "rgba(255,255,255,0.01)", borderRadius: "10px", border: "1px dashed rgba(255,255,255,0.1)" }}>
                  <ListTodo size={32} color="#64748b" style={{ margin: "0 auto 10px auto" }} />
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#e2e8f0" }}>No Investigation Tasks Generated Yet</div>
                  <p style={{ fontSize: "12px", color: "#94a3b8", maxWidth: "460px", margin: "6px auto 14px auto" }}>
                    Click &ldquo;Generate Plan Tasks&rdquo; to build structured diligence tasks for the enabled Financial and Legal workstreams based on the project scope.
                  </p>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleGeneratePlanTasks}
                    disabled={generatingTasks}
                  >
                    Generate Initial Plan Tasks
                  </button>
                </div>
              ) : (
                <div className="data-table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Workstream</th>
                        <th>Task Title & Scope</th>
                        <th>Agent</th>
                        <th>Priority</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {projectTasks.map((t) => (
                        <tr key={t.id}>
                          <td>
                            <span className={`badge badge-${t.workstream}`}>
                              {t.workstream}
                            </span>
                          </td>
                          <td>
                            <div style={{ fontWeight: "600", color: "#f8fafc", fontSize: "13px" }}>{t.title}</div>
                            {t.description && (
                              <div style={{ fontSize: "11.5px", color: "#94a3b8", marginTop: "2px" }}>{t.description}</div>
                            )}
                          </td>
                          <td>
                            <span style={{ fontSize: "11.5px", color: "#a5b4fc", fontFamily: "var(--font-mono)" }}>
                              {t.assigned_agent || "unassigned"}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`badge ${
                                t.priority === "HIGH" ? "badge-high" : t.priority === "MEDIUM" ? "badge-medium" : "badge-verified"
                              }`}
                              style={{ fontSize: "10.5px" }}
                            >
                              {t.priority}
                            </span>
                          </td>
                          <td>
                            <select
                              value={t.status}
                              onChange={(e) => handleUpdateTaskStatus(t.id, e.target.value)}
                              style={{
                                background: t.status === "DONE" ? "rgba(16, 185, 129, 0.15)" : t.status === "IN_PROGRESS" ? "rgba(99, 102, 241, 0.15)" : t.status === "BLOCKED" ? "rgba(239, 68, 68, 0.15)" : "#0f172a",
                                border: `1px solid ${t.status === "DONE" ? "rgba(16, 185, 129, 0.3)" : t.status === "IN_PROGRESS" ? "rgba(99, 102, 241, 0.3)" : t.status === "BLOCKED" ? "rgba(239, 68, 68, 0.3)" : "rgba(255,255,255,0.1)"}`,
                                borderRadius: "6px",
                                color: t.status === "DONE" ? "#34d399" : t.status === "IN_PROGRESS" ? "#818cf8" : t.status === "BLOCKED" ? "#f87171" : "#cbd5e1",
                                fontSize: "11px",
                                fontWeight: "700",
                                padding: "3px 6px",
                                outline: "none",
                                cursor: "pointer"
                              }}
                            >
                              <option value="TODO" style={{ background: "#0f172a", color: "#cbd5e1" }}>TODO</option>
                              <option value="IN_PROGRESS" style={{ background: "#0f172a", color: "#818cf8" }}>IN_PROGRESS</option>
                              <option value="DONE" style={{ background: "#0f172a", color: "#34d399" }}>DONE</option>
                              <option value="BLOCKED" style={{ background: "#0f172a", color: "#f87171" }}>BLOCKED</option>
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="grid-stats">

              <div className="stat-card">
                <div className="stat-header">
                  <span className="stat-label">Ingested Documents</span>
                  <div className="stat-icon"><FileText size={18} /></div>
                </div>
                <div className="stat-val">{documents.length}</div>
                <div className="stat-desc">Processed via Docling & RapidOCR</div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <span className="stat-label">Vector Chunks in DB</span>
                  <div className="stat-icon" style={{ color: "#06b6d4" }}><Database size={18} /></div>
                </div>
                <div className="stat-val">{totalChunks}</div>
                <div className="stat-desc">1024-d BGE-M3 Dense Embeddings</div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <span className="stat-label">Extracted Tables</span>
                  <div className="stat-icon" style={{ color: "#10b981" }}><TableIcon size={18} /></div>
                </div>
                <div className="stat-val">{totalTables}</div>
                <div className="stat-desc">Structured Markdown Tables</div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <span className="stat-label">Persisted Findings</span>
                  <div className="stat-icon" style={{ color: "#f59e0b" }}><ShieldAlert size={18} /></div>
                </div>
                <div className="stat-val">{findings.length}</div>
                <div className="stat-desc">{pendingReviewCount} require human review</div>
              </div>
            </div>

            {/* Architecture Pipeline Banner */}
            <div className="glass-card" style={{ marginBottom: "32px" }}>
              <h2 style={{ fontSize: "17px", fontWeight: "700", marginBottom: "16px", color: "#f8fafc" }}>
                End-to-End Live Workflow Architecture
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "16px", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ color: "#6366f1", fontWeight: "700", fontSize: "12px", marginBottom: "6px" }}>STEP 1: INGESTION</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#f1f5f9" }}>Docling + RapidOCR</div>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Extracts text, table hierarchies, and metadata without data loss.</p>
                </div>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "16px", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ color: "#06b6d4", fontWeight: "700", fontSize: "12px", marginBottom: "6px" }}>STEP 2: CLASSIFICATION</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#f1f5f9" }}>Qwen3 Zero-Shot</div>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Classifies files into Financial, Legal, or Other categories with confidence.</p>
                </div>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "16px", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ color: "#10b981", fontWeight: "700", fontSize: "12px", marginBottom: "6px" }}>STEP 3: KNOWLEDGE BASE</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#f1f5f9" }}>pgvector + BGE-M3</div>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Stores 1024-d dense vectors with cosine similarity index.</p>
                </div>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "16px", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ color: "#f59e0b", fontWeight: "700", fontSize: "12px", marginBottom: "6px" }}>STEP 4: AGENTS</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#f1f5f9" }}>Qwen3 Autonomous DD</div>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Executes real tools, reconciles values, and records findings.</p>
                </div>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "16px", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ color: "#ec4899", fontWeight: "700", fontSize: "12px", marginBottom: "6px" }}>STEP 5: REVIEW</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#f1f5f9" }}>Human-in-the-Loop</div>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>Approve, reject, or request evidence; triggers reanalysis runs.</p>
                </div>
              </div>
            </div>

            {/* Recent Findings Preview */}
            <div className="glass-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: "700" }}>Recent Persisted Findings</h3>
                <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab("findings")}>
                  View All Findings <ArrowRight size={14} />
                </button>
              </div>

              {findings.length === 0 ? (
                <p style={{ color: "#64748b", fontSize: "14px", padding: "20px 0" }}>No findings recorded yet. Run an agent in the Agent Lab to generate findings.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {findings.slice(0, 3).map((f) => (
                    <div key={f.id} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "12px", padding: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "6px" }}>
                          <span className={`badge badge-${f.risk_severity}`}>{f.risk_severity} risk</span>
                          <span className={`badge badge-${f.workstream}`}>{f.workstream}</span>
                          <span style={{ fontSize: "12px", color: "#94a3b8" }}>Status: <strong>{f.status}</strong></span>
                        </div>
                        <h4 style={{ fontSize: "15px", fontWeight: "600", color: "#f8fafc" }}>{f.title}</h4>
                        <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>{f.evidence_conclusion}</p>
                      </div>
                      <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab("findings")}>
                        Inspect
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: DOCUMENTS & INGESTION */}
        {activeTab === "documents" && (
          <div>
            {/* Upload Area */}
            <div className="glass-card" style={{ marginBottom: "28px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "14px" }}>Ingest New Document</h3>
              <form onSubmit={handleUpload} style={{ display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" }}>
                <input
                  type="file"
                  accept=".pdf,.txt,.docx"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  className="input-field"
                  style={{ maxWidth: "340px", padding: "8px 12px" }}
                />
                <button type="submit" className="btn btn-primary" disabled={!selectedFile || uploading}>
                  {uploading ? <RefreshCw className="animate-spin" size={16} /> : <Upload size={16} />}
                  {uploading ? "Ingesting..." : "Run Ingestion Pipeline"}
                </button>
                <button type="button" className="btn btn-secondary" onClick={fetchDocuments}>
                  <RefreshCw size={14} /> Refresh Library
                </button>
              </form>
              {uploadMessage && (
                <div style={{ marginTop: "14px", padding: "10px 14px", borderRadius: "8px", background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)", fontSize: "13px", color: "#c7d2fe" }}>
                  {uploadMessage}
                </div>
              )}
            </div>

            {/* Document Table */}
            <div className="glass-card">
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "16px" }}>Ingested Documents Library</h3>
              {loadingDocs ? (
                <p style={{ color: "#94a3b8", padding: "20px 0" }}>Loading documents...</p>
              ) : documents.length === 0 ? (
                <p style={{ color: "#64748b", padding: "20px 0" }}>No documents found in project {projectId}. Upload a PDF above to begin.</p>
              ) : (
                <div className="data-table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>File Name</th>
                        <th>AI Category</th>
                        <th>Type</th>
                        <th>Chunks</th>
                        <th>Tables</th>
                        <th>Created</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((d) => (
                        <tr key={d.id}>
                          <td style={{ fontWeight: "600", color: "#f8fafc" }}>{d.file_name}</td>
                          <td>
                            <span className={`badge badge-${d.category}`}>
                              {d.category}
                            </span>
                          </td>
                          <td>{d.document_type || "statement"}</td>
                          <td>
                            <span style={{ fontFamily: "var(--font-mono)", color: "#38bdf8" }}>{d.chunk_count}</span>
                          </td>
                          <td>
                            <span style={{ fontFamily: "var(--font-mono)", color: "#34d399" }}>{d.table_count}</span>
                          </td>
                          <td>{d.created_at ? new Date(d.created_at).toLocaleDateString() : "Just now"}</td>
                          <td>
                            {d.table_count > 0 ? (
                              <button className="btn btn-secondary btn-sm" onClick={() => viewTables(d.id)}>
                                <TableIcon size={13} /> View Tables ({d.table_count})
                              </button>
                            ) : (
                              <span style={{ color: "#64748b", fontSize: "12px" }}>No tables</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Extracted Tables Modal */}
            {selectedDocTables && (
              <div className="modal-overlay" onClick={() => setSelectedDocTables(null)}>
                <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "800px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={{ fontSize: "17px", fontWeight: "700" }}>Docling Extracted Markdown Tables</h3>
                    <button className="btn btn-secondary btn-sm" onClick={() => setSelectedDocTables(null)}>Close</button>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px", maxHeight: "60vh", overflowY: "auto" }}>
                    {selectedDocTables.map((t, idx) => (
                      <div key={t.id || idx} style={{ background: "rgba(0,0,0,0.4)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.06)" }}>
                        <div style={{ display: "flex", gap: "10px", marginBottom: "8px", fontSize: "12px", color: "#94a3b8" }}>
                          <span>Page: <strong>{t.page_number}</strong></span>
                          <span>Section: <strong>{t.section || 'General'}</strong></span>
                        </div>
                        <pre className="code-box" style={{ background: "#0b0f19" }}>{t.content}</pre>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: KNOWLEDGE BASE SEARCH */}
        {activeTab === "search" && (
          <div>
            <div className="glass-card" style={{ marginBottom: "24px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "12px" }}>
                pgvector Semantic Search Explorer
              </h3>
              <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "18px" }}>
                Execute live vector similarity queries against 1024-dimensional BGE-M3 embeddings in PostgreSQL.
              </p>

              <form onSubmit={handleSearch} style={{ display: "flex", gap: "12px" }}>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Enter due diligence query (e.g. revenue and gross profit, customer concentration, debt terms)..."
                  className="input-field"
                  style={{ flex: 1 }}
                />
                <button type="submit" className="btn btn-primary" disabled={searching}>
                  {searching ? <RefreshCw className="animate-spin" size={16} /> : <Search size={16} />}
                  {searching ? "Searching..." : "Vector Search"}
                </button>
              </form>
            </div>

            {/* Results Grid */}
            <div className="glass-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <h4 style={{ fontSize: "15px", fontWeight: "700" }}>
                  Search Results ({searchResults.length})
                </h4>
                {searchResults.length > 0 && (
                  <span style={{ fontSize: "12px", color: "#94a3b8" }}>Ranked by Cosine Similarity</span>
                )}
              </div>

              {searching ? (
                <p style={{ color: "#94a3b8", padding: "20px 0" }}>Searching pgvector...</p>
              ) : searchResults.length === 0 ? (
                <p style={{ color: "#64748b", padding: "20px 0" }}>Run a query above to inspect retrieved document chunks and tables.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  {searchResults.map((r, i) => (
                    <div key={r.chunk_id || i} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "12px", padding: "18px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                          <span style={{ fontWeight: "700", color: "#6366f1", fontSize: "13px" }}>#{i + 1}</span>
                          <span style={{ fontWeight: "600", color: "#f8fafc", fontSize: "14px" }}>{r.document_name}</span>
                          <span className="badge badge-verified">Page {r.page_number}</span>
                          {r.section && <span style={{ fontSize: "12px", color: "#94a3b8" }}>[{r.section}]</span>}
                        </div>
                        {r.similarity_score !== undefined && (
                          <span style={{ fontSize: "12px", color: "#34d399", fontFamily: "var(--font-mono)" }}>
                            Score: {(r.similarity_score * 100).toFixed(1)}%
                          </span>
                        )}
                      </div>
                      <div className="code-box" style={{ background: "#080c14" }}>
                        {r.content}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: AGENT INVESTIGATION LAB */}
        {activeTab === "agents" && (
          <div>
            <div className="glass-card" style={{ marginBottom: "24px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "14px" }}>Autonomous Agent Investigation Lab</h3>
              <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "20px" }}>
                Execute real Qwen3 investigation agents with live tool calling against PostgreSQL knowledge base.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "20px", marginBottom: "18px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12.5px", fontWeight: "600", color: "#94a3b8", marginBottom: "8px" }}>
                    Select Agent Workstream
                  </label>
                  <select
                    value={workstream}
                    onChange={(e) => setWorkstream(e.target.value)}
                    className="select-field"
                  >
                    <option value="financial">Financial DD Agent (Tools: metrics, search, reconciliation)</option>
                    <option value="legal">Legal DD Agent (Tools: contract clauses, liabilities)</option>
                    <option value="cross_domain">Cross-Domain Agent (Reconciliation across workstreams)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12.5px", fontWeight: "600", color: "#94a3b8", marginBottom: "8px" }}>
                    Investigation Objective
                  </label>
                  <textarea
                    rows={3}
                    value={objective}
                    onChange={(e) => setObjective(e.target.value)}
                    className="textarea-field"
                    placeholder="Define the autonomous investigation objective..."
                  />
                </div>
              </div>

              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <button
                  onClick={handleRunAgent}
                  className="btn btn-primary"
                  disabled={runningAgent || orchestratorRunning}
                >
                  {runningAgent ? <RefreshCw className="animate-spin" size={16} /> : <Bot size={16} />}
                  {runningAgent ? "Agent Running Investigation..." : "Launch Single Agent"}
                </button>
                <button
                  onClick={() => {
                    setActiveTab("overview");
                    handleRunFullDD();
                  }}
                  className="btn btn-secondary"
                  disabled={runningAgent || orchestratorRunning}
                >
                  <Play size={16} color="#818cf8" />
                  Run Central Full DD Pipeline
                </button>
              </div>
            </div>


            {/* Agent Execution Trace */}
            {agentResult && (
              <div className="glass-card">
                <h4 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <CheckCircle2 color="#10b981" size={18} /> Investigation Run Trace
                </h4>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginBottom: "18px" }}>
                  <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>STATUS</div>
                    <div style={{ fontSize: "14px", fontWeight: "700", color: "#34d399" }}>{agentResult.status}</div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>ITERATIONS</div>
                    <div style={{ fontSize: "14px", fontWeight: "700" }}>{agentResult.iterations}</div>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px", borderRadius: "8px" }}>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>PERSISTED FINDINGS</div>
                    <div style={{ fontSize: "14px", fontWeight: "700", color: "#6366f1" }}>{agentResult.persisted_findings_count}</div>
                  </div>
                </div>

                <div style={{ marginBottom: "16px" }}>
                  <h5 style={{ fontSize: "13px", fontWeight: "600", color: "#94a3b8", marginBottom: "8px" }}>Executed Tool Calls</h5>
                  {agentResult.tool_calls && agentResult.tool_calls.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {agentResult.tool_calls.map((tc, idx) => (
                        <div key={idx} style={{ background: "#0a0e18", padding: "12px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
                          <span style={{ color: "#818cf8", fontWeight: "600", fontSize: "13px" }}>tool: {tc.name}</span>
                          <pre style={{ color: "#94a3b8", fontSize: "12px", marginTop: "4px" }}>{JSON.stringify(tc.arguments, null, 2)}</pre>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: "#64748b", fontSize: "13px" }}>No tools called.</p>
                  )}
                </div>

                <div>
                  <h5 style={{ fontSize: "13px", fontWeight: "600", color: "#94a3b8", marginBottom: "8px" }}>Model Response & Reasoning</h5>
                  <div className="code-box" style={{ background: "#0a0e18", color: "#e2e8f0" }}>
                    {agentResult.final_answer || "Investigation completed and findings persisted."}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 5: FINDINGS & HUMAN REVIEW */}
        {activeTab === "findings" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: "700" }}>Persisted Findings & Evidence Review</h3>
                <p style={{ fontSize: "13px", color: "#94a3b8" }}>
                  Grounded findings stored in PostgreSQL with source traceability and human review decisions.
                </p>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => { fetchFindings(); fetchReanalysis(); fetchRequests(); }}>
                <RefreshCw size={14} /> Refresh Findings
              </button>
            </div>

            {/* Active Evidence Requests & Reanalysis Pipeline */}
            <div className="glass-card" style={{ marginBottom: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
                    <Layers size={18} color="#818cf8" />
                    Automated Reanalysis Queue & Requests ({reanalysisRuns.length})
                  </h4>
                  <p style={{ fontSize: "12.5px", color: "#94a3b8", marginTop: "2px" }}>
                    Track reviewer-requested clarification jobs, background worker status, and reinvestigation summaries.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      fetchReanalysis();
                      fetchRequests();
                    }}
                    disabled={loadingReanalysis}
                  >
                    <RefreshCw size={14} className={loadingReanalysis ? "animate-spin" : ""} /> Refresh Queue
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleTriggerWorker}
                    disabled={triggeringWorker}
                  >
                    <Play size={14} /> {triggeringWorker ? "Worker Running..." : "Process Next Job"}
                  </button>
                </div>
              </div>

              {reanalysisRuns.length === 0 ? (
                <p style={{ fontSize: "13px", color: "#64748b", padding: "10px 0" }}>
                  No active or past reanalysis runs for project {projectId}. Click &ldquo;Request Evidence&rdquo; on any finding to queue an automated follow-up investigation.
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {reanalysisRuns.slice(0, 5).map((run) => (
                    <div key={run.id} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "10px", padding: "12px 16px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px", flexWrap: "wrap", gap: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "#94a3b8" }}>
                            Run #{run.id.substring(0, 8)}
                          </span>
                          <span style={{ fontSize: "12.5px", fontWeight: "600", color: "#f8fafc" }}>
                            Trigger: {run.trigger_type}
                          </span>
                        </div>
                        <span className={`badge ${run.status === 'COMPLETE' ? 'badge-low' : run.status === 'RUNNING' ? 'badge-verified' : run.status === 'FAILED' ? 'badge-high' : 'badge-medium'}`} style={{ fontSize: "10.5px" }}>
                          {run.status}
                        </span>
                      </div>
                      {run.reason && (
                        <p style={{ fontSize: "12.5px", color: "#cbd5e1", marginBottom: "6px" }}>
                          <strong>Clarification Request:</strong> {run.reason}
                        </p>
                      )}
                      {run.result_summary && (
                        <div style={{ fontSize: "12px", color: run.status === 'FAILED' ? "#f87171" : "#34d399", background: "rgba(0,0,0,0.25)", padding: "8px 12px", borderRadius: "6px", borderLeft: `3px solid ${run.status === 'FAILED' ? '#ef4444' : '#10b981'}` }}>
                          <strong>Worker Result:</strong> {run.result_summary}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Workstream Filter Bar */}
            <div style={{ display: "flex", gap: "10px", marginBottom: "16px", alignItems: "center", flexWrap: "wrap" }}>
              <span style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600", textTransform: "uppercase" }}>Workstream:</span>
              {["ALL", "financial", "legal", "cross_domain"].map(filterKey => {
                const count = filterKey === "ALL" ? findings.length : findings.filter(f => (f.workstream || "").toLowerCase() === filterKey.toLowerCase()).length;
                const isActive = findingFilter.toLowerCase() === filterKey.toLowerCase();
                const label = filterKey === "ALL" ? "All Findings" : filterKey === "cross_domain" ? "Cross-Domain" : filterKey.charAt(0).toUpperCase() + filterKey.slice(1);
                return (
                  <button
                    key={filterKey}
                    onClick={() => setFindingFilter(filterKey)}
                    style={{
                      background: isActive ? "#4f46e5" : "rgba(255,255,255,0.04)",
                      color: isActive ? "#ffffff" : "#94a3b8",
                      border: isActive ? "1px solid #6366f1" : "1px solid rgba(255,255,255,0.08)",
                      borderRadius: "6px",
                      padding: "5px 12px",
                      fontSize: "12px",
                      fontWeight: "600",
                      cursor: "pointer",
                    }}
                  >
                    {label} ({count})
                  </button>
                );
              })}
            </div>

            {loadingFindings ? (
              <p style={{ color: "#94a3b8" }}>Loading findings...</p>
            ) : findings.length === 0 ? (
              <div className="glass-card" style={{ textAlign: "center", padding: "40px" }}>
                <ShieldAlert size={36} color="#64748b" style={{ margin: "0 auto 12px" }} />
                <h4 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc" }}>No findings recorded yet</h4>
                <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "6px" }}>
                  Run an autonomous investigation in the Agent Lab to record verified findings.
                </p>
              </div>
            ) : findings.filter(f => findingFilter === "ALL" || (f.workstream || "").toLowerCase() === findingFilter.toLowerCase()).length === 0 ? (
              <div className="glass-card" style={{ textAlign: "center", padding: "30px" }}>
                <p style={{ fontSize: "13.5px", color: "#94a3b8" }}>No {findingFilter} findings found for this project.</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                {findings
                  .filter(f => findingFilter === "ALL" || (f.workstream || "").toLowerCase() === findingFilter.toLowerCase())
                  .map((f) => (
                  <div key={f.id} className="glass-card">
                    {/* Header */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", marginBottom: "14px" }}>
                      <div>
                        <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "8px" }}>
                          <span className={`badge badge-${f.risk_severity}`}>{f.risk_severity} risk</span>
                          <span className={`badge badge-${f.workstream}`}>{f.workstream}</span>
                          <span style={{ fontSize: "12px", color: "#94a3b8" }}>Confidence: <strong>{(parseFloat(f.confidence || 0.9) * 100).toFixed(0)}%</strong></span>
                          <span style={{ fontSize: "12px", color: f.status === "APPROVED" ? "#34d399" : f.status === "REJECTED" ? "#f87171" : "#fbbf24" }}>
                            ● <strong>{f.status}</strong>
                          </span>
                        </div>
                        <h4 style={{ fontSize: "17px", fontWeight: "700", color: "#f8fafc" }}>{f.title}</h4>
                      </div>

                      {/* Review Buttons */}
                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          className="btn btn-success btn-sm"
                          onClick={() => submitReview(f.id, "APPROVE")}
                          disabled={submittingReview || f.status === "APPROVED"}
                        >
                          <CheckCircle2 size={14} /> Approve
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => submitReview(f.id, "REJECT")}
                          disabled={submittingReview || f.status === "REJECTED"}
                        >
                          <XCircle size={14} /> Reject
                        </button>
                        <button
                          className="btn btn-warning btn-sm"
                          onClick={() => setReviewModal({ isOpen: true, findingId: f.id, action: "REQUEST_MORE_EVIDENCE" })}
                          disabled={submittingReview}
                        >
                          <HelpCircle size={14} /> Request Evidence
                        </button>
                      </div>
                    </div>

                    {/* Details */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.04)" }}>
                        <div style={{ fontSize: "11px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", marginBottom: "4px" }}>Issue</div>
                        <p style={{ fontSize: "13.5px", color: "#cbd5e1" }}>{f.issue}</p>
                      </div>
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: "14px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.04)" }}>
                        <div style={{ fontSize: "11px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", marginBottom: "4px" }}>Why It Matters</div>
                        <p style={{ fontSize: "13.5px", color: "#cbd5e1" }}>{f.why_it_matters || "Material transaction risk factor"}</p>
                      </div>
                    </div>

                    <div style={{ background: "rgba(99,102,241,0.05)", padding: "14px", borderRadius: "10px", border: "1px solid rgba(99,102,241,0.15)", marginBottom: "16px" }}>
                      <div style={{ fontSize: "11px", fontWeight: "700", color: "#a5b4fc", textTransform: "uppercase", marginBottom: "4px" }}>Conclusion</div>
                      <p style={{ fontSize: "14px", color: "#f8fafc", fontWeight: "500" }}>{f.evidence_conclusion}</p>
                    </div>

                    {/* Evidence Drawer */}
                    {f.evidence && f.evidence.length > 0 && (
                      <div>
                        <h5 style={{ fontSize: "13px", fontWeight: "700", color: "#94a3b8", marginBottom: "10px" }}>
                          Cited Evidence & Source Traceability ({f.evidence.length})
                        </h5>
                        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                          {f.evidence.map((ev, idx) => {
                            const statusBadge =
                              ev.validation_status === 'VERIFIED' ? 'badge-verified' :
                              ev.validation_status === 'FLAGGED_DISCREPANCY' ? 'badge-discrepancy' :
                              ev.validation_status === 'AMBIGUOUS' ? 'badge-ambiguous' :
                              ev.validation_status === 'UNSUPPORTED_CLAIM' ? 'badge-high' :
                              'badge-unverified';

                            return (
                              <div key={ev.id || idx} style={{ background: "#0a0e18", padding: "14px 16px", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.06)" }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", flexWrap: "wrap", gap: "8px" }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                                    <span style={{ fontSize: "13px", color: "#38bdf8", fontWeight: "700" }}>
                                      {ev.source_label || "Source Document"}
                                    </span>
                                    {ev.page_number && (
                                      <span style={{ fontSize: "11.5px", color: "#94a3b8", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "4px" }}>
                                        Page {ev.page_number}
                                      </span>
                                    )}
                                    {ev.chunk_id && (
                                      <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "#64748b" }}>
                                        Chunk: {ev.chunk_id.substring(0, 16)}...
                                      </span>
                                    )}
                                  </div>
                                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    {ev.match_method && ev.match_method !== "none" && (
                                      <span style={{ fontSize: "11px", color: "#a5b4fc", fontFamily: "var(--font-mono)" }}>
                                        {ev.match_method} {ev.confidence ? `(${(ev.confidence * 100).toFixed(0)}%)` : ''}
                                      </span>
                                    )}
                                    <span className={`badge ${statusBadge}`}>
                                      {ev.validation_status}
                                    </span>
                                  </div>
                                </div>

                                {ev.extracted_value && (
                                  <div style={{ fontSize: "12px", color: "#34d399", marginBottom: "6px", fontFamily: "var(--font-mono)" }}>
                                    Extracted Value: <strong>{ev.extracted_value}</strong>
                                  </div>
                                )}

                                {ev.quoted_text && (
                                  <pre className="code-box" style={{ background: "#06090e", marginBottom: "8px", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                                    {ev.quoted_text}
                                  </pre>
                                )}

                                {ev.validation_reason && (
                                  <div style={{ fontSize: "12px", color: ev.validation_status === 'VERIFIED' ? "#34d399" : ev.validation_status === 'FLAGGED_DISCREPANCY' ? "#fca5a5" : "#94a3b8", background: "rgba(255,255,255,0.02)", padding: "6px 10px", borderRadius: "6px", borderLeft: `3px solid ${ev.validation_status === 'VERIFIED' ? '#10b981' : ev.validation_status === 'FLAGGED_DISCREPANCY' ? '#ef4444' : '#64748b'}` }}>
                                    <strong>Validation Note:</strong> {ev.validation_reason}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Review History & Audit Trail */}
                    {f.reviews && f.reviews.length > 0 && (
                      <div style={{ marginTop: "16px", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "14px" }}>
                        <h5 style={{ fontSize: "12px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
                          <FileCheck size={14} color="#818cf8" /> Review Audit History ({f.reviews.length})
                        </h5>
                        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                          {f.reviews.map((r, rIdx) => (
                            <div key={r.id || rIdx} style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "8px", padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                              <div>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                                  <span className={`badge ${r.action === 'APPROVE' ? 'badge-low' : r.action === 'REJECT' ? 'badge-high' : 'badge-medium'}`} style={{ fontSize: "10px", padding: "2px 8px" }}>
                                    {r.action}
                                  </span>
                                  <span style={{ fontSize: "12px", fontWeight: "600", color: "#f8fafc" }}>
                                    {r.reviewer}
                                  </span>
                                  {r.reviewed_at && (
                                    <span style={{ fontSize: "11px", color: "#64748b" }}>
                                      {new Date(r.reviewed_at).toLocaleString()}
                                    </span>
                                  )}
                                </div>
                                {r.comment && (
                                  <p style={{ fontSize: "12.5px", color: "#cbd5e1" }}>
                                    &ldquo;{r.comment}&rdquo;
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Review Comment Modal */}
            {reviewModal.isOpen && (
              <div className="modal-overlay" onClick={() => setReviewModal({ isOpen: false, findingId: null, action: "REQUEST_MORE_EVIDENCE" })}>
                <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                  <h3 style={{ fontSize: "17px", fontWeight: "700" }}>Request More Evidence</h3>
                  <p style={{ fontSize: "13px", color: "#94a3b8" }}>
                    Submitting this request will automatically generate an open DDRequest, create a pending task, and schedule an automated reanalysis run in PostgreSQL.
                  </p>
                  <textarea
                    rows={4}
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                    placeholder="Describe what additional evidence or documentation is needed..."
                    className="textarea-field"
                  />
                  <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => setReviewModal({ isOpen: false, findingId: null, action: "REQUEST_MORE_EVIDENCE" })}
                    >
                      Cancel
                    </button>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => submitReview(reviewModal.findingId, reviewModal.action, reviewComment)}
                      disabled={submittingReview}
                    >
                      {submittingReview ? "Submitting..." : "Submit & Trigger Reanalysis"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 6: DD CHATBOT & EVIDENCE QA */}
        {activeTab === "chat" && (
          <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "20px", alignItems: "start" }}>
            {/* Sidebar: Conversation List */}
            <div className="glass-card" style={{ padding: "18px", height: "calc(100vh - 220px)", display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <MessageSquare size={17} color="#818cf8" />
                  <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>Chat Sessions</h3>
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => handleCreateNewConversation("New Due Diligence Chat")}
                  style={{ padding: "4px 8px", fontSize: "11.5px", display: "flex", alignItems: "center", gap: "4px" }}
                  title="Start New Chat"
                >
                  <Plus size={12} /> New
                </button>
              </div>

              <div style={{ fontSize: "11.5px", color: "#94a3b8", marginBottom: "10px" }}>
                Project: <strong style={{ color: "#cbd5e1" }}>{currentProject?.target_company || projectId}</strong>
              </div>

              {/* Conversation items list */}
              <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px", paddingRight: "4px" }}>
                {loadingConversations ? (
                  <p style={{ color: "#64748b", fontSize: "12px", padding: "10px 0" }}>Loading chat sessions...</p>
                ) : conversationsList.length === 0 ? (
                  <div style={{ padding: "20px 10px", textAlign: "center", color: "#64748b", fontSize: "12px" }}>
                    No chat sessions yet. Click &ldquo;+ New&rdquo; to start asking questions.
                  </div>
                ) : (
                  conversationsList.map((c) => {
                    const isActive = c.id === activeConversationId;
                    return (
                      <div
                        key={c.id}
                        onClick={() => setActiveConversationId(c.id)}
                        style={{
                          padding: "10px 12px",
                          borderRadius: "8px",
                          background: isActive ? "rgba(99, 102, 241, 0.15)" : "rgba(255, 255, 255, 0.02)",
                          border: `1px solid ${isActive ? "rgba(99, 102, 241, 0.4)" : "rgba(255, 255, 255, 0.05)"}`,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: "8px"
                        }}
                      >
                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                          <div style={{ fontSize: "12.5px", fontWeight: isActive ? "700" : "500", color: isActive ? "#f8fafc" : "#cbd5e1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {c.title}
                          </div>
                          <div style={{ fontSize: "10.5px", color: "#64748b", marginTop: "2px" }}>
                            {c.message_count || 0} messages • {new Date(c.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => handleDeleteConversation(c.id, e)}
                          title="Delete Session"
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "#64748b",
                            cursor: "pointer",
                            padding: "2px 4px",
                            borderRadius: "4px",
                            opacity: isActive ? 1 : 0.6
                          }}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Main Chat Thread Area */}
            <div className="glass-card" style={{ padding: "0", height: "calc(100vh - 220px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
              {/* Chat Thread Header */}
              <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(255, 255, 255, 0.06)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(10, 14, 26, 0.6)" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Bot size={18} color="#818cf8" />
                    <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#f8fafc" }}>
                      {activeConversationDetail?.title || "Evidence-Grounded Due Diligence Chat"}
                    </h3>
                  </div>
                  <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "2px" }}>
                    Grounding on {documents.length} project documents and {findings.length} findings • Qwen3 (11434)
                  </div>
                </div>

                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <span className="badge badge-verified" style={{ fontSize: "11px" }}>
                    Project: {projectId}
                  </span>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleCreateNewConversation("New Due Diligence Chat")}
                    style={{ fontSize: "11px", padding: "3px 8px" }}
                  >
                    <Plus size={11} /> New Chat
                  </button>
                </div>
              </div>

              {/* Messages Scroll Area */}
              <div style={{ flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
                {(!activeConversationDetail || !activeConversationDetail.messages || activeConversationDetail.messages.length === 0) ? (
                  /* Empty State / Welcome Screen */
                  <div style={{ margin: "auto", textAlign: "center", maxWidth: "620px", padding: "30px 20px" }}>
                    <div style={{ background: "rgba(99, 102, 241, 0.15)", width: "54px", height: "54px", borderRadius: "14px", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px auto", color: "#818cf8" }}>
                      <MessageSquare size={26} />
                    </div>
                    <h3 style={{ fontSize: "19px", fontWeight: "700", color: "#f8fafc", marginBottom: "8px" }}>
                      Evidence-Grounded Due Diligence Assistant
                    </h3>
                    <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: "1.6", marginBottom: "22px" }}>
                      Ask questions regarding reported revenue, EBITDA margins, debt covenants, customer agreements, IP rights, or existing findings for <strong>{currentProject?.target_company || "the target company"}</strong>. Answers cite exact document names, pages, and chunk references.
                    </p>

                    <div style={{ textAlign: "left" }}>
                      <div style={{ fontSize: "12px", fontWeight: "700", color: "#cbd5e1", textTransform: "uppercase", marginBottom: "10px" }}>
                        Suggested Diligence Questions:
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {[
                          "What was the reported revenue and gross profit for FY 2025-26?",
                          "Are there any debt restrictions, credit covenants, or encumbrances?",
                          "Summarize the top due diligence risk findings and their severities.",
                          "What are the change of control clauses or termination covenants in agreements?"
                        ].map((promptText, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => handleSendChatMessage(null, promptText)}
                            style={{
                              background: "rgba(255, 255, 255, 0.02)",
                              border: "1px solid rgba(255, 255, 255, 0.07)",
                              borderRadius: "8px",
                              padding: "10px 14px",
                              textAlign: "left",
                              fontSize: "12.5px",
                              color: "#cbd5e1",
                              cursor: "pointer",
                              transition: "all 0.15s ease",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center"
                            }}
                          >
                            <span>{promptText}</span>
                            <ArrowRight size={13} color="#818cf8" />
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Render Message Thread */
                  activeConversationDetail.messages.map((msg, i) => {
                    const isUser = msg.role === "user";
                    return (
                      <div
                        key={msg.id || i}
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: isUser ? "flex-end" : "flex-start",
                          maxWidth: "100%"
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px", fontSize: "11px", color: "#64748b" }}>
                          {isUser ? (
                            <>
                              <span>You</span>
                              <User size={12} color="#a5b4fc" />
                            </>
                          ) : (
                            <>
                              <Bot size={12} color="#818cf8" />
                              <span>DD Assistant (Llama)</span>
                            </>
                          )}
                          <span>• {new Date(msg.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>

                        {/* Bubble */}
                        <div
                          style={{
                            maxWidth: isUser ? "80%" : "90%",
                            padding: "14px 18px",
                            borderRadius: isUser ? "14px 14px 2px 14px" : "14px 14px 14px 2px",
                            background: isUser ? "linear-gradient(135deg, rgba(79, 70, 229, 0.4) 0%, rgba(99, 102, 241, 0.3) 100%)" : "rgba(16, 23, 38, 0.85)",
                            border: `1px solid ${isUser ? "rgba(99, 102, 241, 0.5)" : "rgba(255, 255, 255, 0.08)"}`,
                            color: "#f8fafc",
                            fontSize: "13.5px",
                            lineHeight: "1.65",
                            whiteSpace: "pre-wrap"
                          }}
                        >
                          {msg.content}

                          {/* Insufficient Evidence Warning Pill */}
                          {msg.is_insufficient_evidence && (
                            <div style={{ marginTop: "10px", padding: "8px 12px", borderRadius: "6px", background: "rgba(245, 158, 11, 0.12)", border: "1px solid rgba(245, 158, 11, 0.3)", display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#fbbf24" }}>
                              <AlertTriangle size={14} />
                              <span>Insufficient documentation in project library for a conclusive answer.</span>
                            </div>
                          )}

                          {/* Cited Sources Drawer / Cards */}
                          {msg.sources && msg.sources.length > 0 && (
                            <div style={{ marginTop: "14px", paddingTop: "12px", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
                              <div style={{ fontSize: "11.5px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                                <Layers size={13} color="#38bdf8" />
                                Supporting Evidence & Citations ({msg.sources.length})
                              </div>
                              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "8px" }}>
                                {msg.sources.map((src, sIdx) => (
                                  <div
                                    key={sIdx}
                                    style={{
                                      background: "#080c14",
                                      padding: "10px 12px",
                                      borderRadius: "8px",
                                      border: "1px solid rgba(255, 255, 255, 0.05)",
                                      fontSize: "11.5px"
                                    }}
                                  >
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                                      <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#38bdf8", fontWeight: "600", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                        {src.source_type === "finding" ? <ShieldAlert size={12} color="#f59e0b" /> : <FileText size={12} />}
                                        <span title={src.document_name}>{src.document_name}</span>
                                      </div>
                                      <span
                                        className={`badge ${src.validation_status === 'VERIFIED' ? 'badge-verified' : src.source_type === 'finding' ? 'badge-medium' : ''}`}
                                        style={{ fontSize: "9.5px", padding: "1px 6px" }}
                                      >
                                        {src.validation_status === 'VERIFIED' ? 'Verified Quote' : src.page_number ? `Page ${src.page_number}` : 'Evidence'}
                                      </span>
                                    </div>
                                    <p style={{ color: "#94a3b8", margin: 0, fontStyle: "italic", fontSize: "11px", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                                      &ldquo;{src.snippet}&rdquo;
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}

                {/* Loading State Bubble */}
                {sendingChat && (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", maxWidth: "90%" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px", fontSize: "11px", color: "#64748b" }}>
                      <Bot size={12} color="#818cf8" />
                      <span>DD Assistant (Llama)</span>
                    </div>
                    <div
                      style={{
                        padding: "14px 18px",
                        borderRadius: "14px 14px 14px 2px",
                        background: "rgba(16, 23, 38, 0.85)",
                        border: "1px solid rgba(99, 102, 241, 0.3)",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        color: "#c7d2fe",
                        fontSize: "13px"
                      }}
                    >
                      <RefreshCw className="animate-spin" size={16} color="#818cf8" />
                      <span>Retrieving project evidence from pgvector & generating answer with Llama...</span>
                    </div>
                  </div>
                )}

                {/* Error Banner */}
                {chatError && (
                  <div style={{ padding: "10px 14px", borderRadius: "8px", background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#fca5a5", fontSize: "12.5px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <AlertTriangle size={15} />
                    <span>{chatError}</span>
                  </div>
                )}
              </div>

              {/* Chat Input Bar */}
              <div style={{ padding: "14px 20px", borderTop: "1px solid rgba(255, 255, 255, 0.06)", background: "rgba(10, 14, 26, 0.8)" }}>
                <form
                  onSubmit={handleSendChatMessage}
                  style={{ display: "flex", gap: "10px", alignItems: "center" }}
                >
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder={`Ask a question about ${currentProject?.target_company || "the company"}'s documents or findings...`}
                    className="input-field"
                    style={{ flex: 1, padding: "10px 14px", fontSize: "13px" }}
                    disabled={sendingChat}
                  />
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={sendingChat || !chatInput.trim()}
                    style={{ padding: "10px 18px", fontWeight: "600", display: "flex", alignItems: "center", gap: "6px" }}
                  >
                    {sendingChat ? <RefreshCw className="animate-spin" size={15} /> : <Send size={15} />}
                    <span>{sendingChat ? "Answering..." : "Ask Bot"}</span>
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* TAB 7: FINAL DD REPORT & EXPORT */}
        {activeTab === "report" && (
          <div>
            {/* Header / Actions Card */}
            <div className="glass-card" style={{ marginBottom: "22px", background: "linear-gradient(180deg, rgba(16, 23, 38, 0.95) 0%, rgba(10, 14, 26, 0.9) 100%)", border: "1px solid rgba(99, 102, 241, 0.3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                    <div style={{ background: "rgba(99, 102, 241, 0.2)", padding: "7px", borderRadius: "8px", color: "#818cf8" }}>
                      <FileText size={20} />
                    </div>
                    <div>
                      <h2 style={{ fontSize: "20px", fontWeight: "700", color: "#f8fafc" }}>
                        {reportData?.metadata?.target_company ? `${reportData.metadata.target_company} — Due Diligence Report` : "Final Due Diligence Report & Export"}
                      </h2>
                      <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "2px" }}>
                        Project: <strong style={{ color: "#cbd5e1" }}>{currentProject?.name || projectId}</strong> &nbsp;•&nbsp;
                        Period: <span style={{ color: "#fbbf24" }}>{reportData?.metadata?.diligence_period || "FY 2025-26"}</span> &nbsp;•&nbsp;
                        Deal: <span style={{ color: "#38bdf8" }}>{reportData?.metadata?.deal_type || "Acquisition"}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Export & Refresh Actions */}
                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => fetchReportPreview()}
                    disabled={loadingReport}
                    style={{ display: "flex", alignItems: "center", gap: "6px" }}
                  >
                    <RefreshCw className={loadingReport ? "animate-spin" : ""} size={14} />
                    <span>{loadingReport ? "Compiling..." : "Refresh Report"}</span>
                  </button>

                  <button
                    className="btn btn-primary"
                    onClick={() => handleDownloadPdf()}
                    disabled={downloadingPdf || !reportData}
                    style={{ background: "linear-gradient(135deg, #4338ca 0%, #6366f1 100%)", display: "flex", alignItems: "center", gap: "6px", fontWeight: "600" }}
                    title="Export publication-quality PDF report with running headers & tables"
                  >
                    {downloadingPdf ? <RefreshCw className="animate-spin" size={14} /> : <Download size={14} />}
                    <span>{downloadingPdf ? "Generating PDF..." : "Download Executive PDF"}</span>
                  </button>

                  <button
                    className="btn btn-secondary"
                    onClick={() => handleDownloadJson()}
                    disabled={downloadingJson || !reportData}
                    style={{ display: "flex", alignItems: "center", gap: "6px" }}
                    title="Export structured JSON report for machine integration"
                  >
                    {downloadingJson ? <RefreshCw className="animate-spin" size={14} /> : <Download size={14} />}
                    <span>{downloadingJson ? "Exporting..." : "Download JSON"}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Loading State */}
            {loadingReport && (
              <div className="glass-card" style={{ padding: "40px", textAlign: "center", marginBottom: "22px" }}>
                <RefreshCw className="animate-spin" size={32} color="#818cf8" style={{ margin: "0 auto 14px auto" }} />
                <h3 style={{ fontSize: "16px", color: "#f8fafc", fontWeight: "600" }}>Compiling Due Diligence Report</h3>
                <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                  Aggregating findings, evidence citations, validation records, scope questions, and review history...
                </p>
              </div>
            )}

            {/* Error State */}
            {reportError && (
              <div style={{ padding: "14px 18px", borderRadius: "10px", background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#fca5a5", fontSize: "13px", display: "flex", alignItems: "center", gap: "10px", marginBottom: "22px" }}>
                <AlertTriangle size={18} />
                <span>{reportError}</span>
              </div>
            )}

            {/* Main Report Body */}
            {reportData && !loadingReport && (
              <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
                {/* 1. Executive Summary KPIs */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "14px" }}>
                  <div className="glass-card" style={{ padding: "16px" }}>
                    <div style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase", fontWeight: "700" }}>Total Findings</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#f8fafc", marginTop: "4px" }}>
                      {reportData.executive_summary.total_findings}
                    </div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                      {reportData.executive_summary.financial_count} Financial • {reportData.executive_summary.legal_count} Legal • {reportData.executive_summary.cross_domain_count} Cross-Domain
                    </div>
                  </div>

                  <div className="glass-card" style={{ padding: "16px", borderLeft: "4px solid #ef4444" }}>
                    <div style={{ fontSize: "11px", color: "#f87171", textTransform: "uppercase", fontWeight: "700" }}>High Risk Issues</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#ef4444", marginTop: "4px" }}>
                      {reportData.executive_summary.high_risk_count}
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>
                      {reportData.executive_summary.medium_risk_count} Medium • {reportData.executive_summary.low_risk_count} Low Risk
                    </div>
                  </div>

                  <div className="glass-card" style={{ padding: "16px", borderLeft: "4px solid #10b981" }}>
                    <div style={{ fontSize: "11px", color: "#34d399", textTransform: "uppercase", fontWeight: "700" }}>Approved Findings</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#10b981", marginTop: "4px" }}>
                      {reportData.executive_summary.approved_count}
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>
                      Confirmed by lead reviewer
                    </div>
                  </div>

                  <div className="glass-card" style={{ padding: "16px", borderLeft: "4px solid #f59e0b" }}>
                    <div style={{ fontSize: "11px", color: "#fbbf24", textTransform: "uppercase", fontWeight: "700" }}>Pending Review</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#f59e0b", marginTop: "4px" }}>
                      {reportData.executive_summary.pending_review_count}
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>
                      {reportData.executive_summary.more_evidence_required_count} More Evidence Req.
                    </div>
                  </div>

                  <div className="glass-card" style={{ padding: "16px", borderLeft: "4px solid #38bdf8" }}>
                    <div style={{ fontSize: "11px", color: "#38bdf8", textTransform: "uppercase", fontWeight: "700" }}>Unverified Evidence</div>
                    <div style={{ fontSize: "28px", fontWeight: "800", color: "#38bdf8", marginTop: "4px" }}>
                      {reportData.executive_summary.unverified_evidence_count}
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>
                      Flagged by evidence validator
                    </div>
                  </div>
                </div>

                {/* 2. Executive Synthesis Overview */}
                <div className="glass-card" style={{ padding: "20px 24px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                    <ShieldAlert size={16} color="#818cf8" />
                    <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>Executive Summary Overview</h3>
                  </div>
                  <p style={{ fontSize: "13.5px", color: "#cbd5e1", lineHeight: "1.7", margin: 0, fontStyle: "italic" }}>
                    &ldquo;{reportData.executive_summary.executive_overview}&rdquo;
                  </p>
                </div>

                {/* 3. Scope & Workstreams Summary */}
                <div className="glass-card" style={{ padding: "18px 22px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                    <Settings size={16} color="#34d399" />
                    <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>Diligence Scope & Enabled Workstreams</h3>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
                    {reportData.scope.workstream_details.map((ws, idx) => (
                      <div key={idx} style={{ background: "rgba(255,255,255,0.02)", padding: "12px 14px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                          <span style={{ fontSize: "12.5px", fontWeight: "700", color: "#f8fafc", textTransform: "capitalize" }}>
                            {ws.workstream} Due Diligence
                          </span>
                          <span className={`badge ${ws.is_enabled ? 'badge-verified' : 'badge-medium'}`} style={{ fontSize: "10px" }}>
                            {ws.is_enabled ? "Enabled" : "Disabled"}
                          </span>
                        </div>
                        <div style={{ fontSize: "11.5px", color: "#94a3b8" }}>
                          Questions: <strong>{ws.custom_questions?.length || 0}</strong> &nbsp;•&nbsp;
                          Review Areas: <strong>{ws.review_areas?.length || 0}</strong>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 4. Findings Section with Workstream Filter */}
                <div className="glass-card" style={{ padding: "20px 24px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "18px", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <Layers size={17} color="#818cf8" />
                      <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#f8fafc" }}>
                        Recorded Findings Breakdown ({reportData.all_findings.length})
                      </h3>
                    </div>

                    {/* Filter buttons */}
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        className={`btn btn-sm ${reportFilter === "all" ? "btn-primary" : "btn-secondary"}`}
                        onClick={() => setReportFilter("all")}
                        style={{ fontSize: "11.5px" }}
                      >
                        All ({reportData.all_findings.length})
                      </button>
                      <button
                        className={`btn btn-sm ${reportFilter === "financial" ? "btn-primary" : "btn-secondary"}`}
                        onClick={() => setReportFilter("financial")}
                        style={{ fontSize: "11.5px" }}
                      >
                        Financial ({reportData.financial_findings.length})
                      </button>
                      <button
                        className={`btn btn-sm ${reportFilter === "legal" ? "btn-primary" : "btn-secondary"}`}
                        onClick={() => setReportFilter("legal")}
                        style={{ fontSize: "11.5px" }}
                      >
                        Legal ({reportData.legal_findings.length})
                      </button>
                      <button
                        className={`btn btn-sm ${reportFilter === "cross_domain" ? "btn-primary" : "btn-secondary"}`}
                        onClick={() => setReportFilter("cross_domain")}
                        style={{ fontSize: "11.5px" }}
                      >
                        Cross-Domain ({reportData.cross_domain_findings.length})
                      </button>
                    </div>
                  </div>

                  {/* Findings Cards List */}
                  {(() => {
                    const filtered = reportFilter === "financial"
                      ? reportData.financial_findings
                      : reportFilter === "legal"
                      ? reportData.legal_findings
                      : reportFilter === "cross_domain"
                      ? reportData.cross_domain_findings
                      : reportData.all_findings;

                    if (filtered.length === 0) {
                      return (
                        <div style={{ padding: "30px", textAlign: "center", color: "#64748b", fontSize: "13px" }}>
                          No findings recorded in this workstream category.
                        </div>
                      );
                    }

                    return (
                      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                        {filtered.map((item) => {
                          const isHigh = item.risk_severity.toLowerCase() === "high";
                          const isMed = item.risk_severity.toLowerCase() === "medium";
                          const isApproved = item.status.toUpperCase() === "APPROVED" || item.status.toUpperCase() === "ACCEPTED";
                          const isRejected = item.status.toUpperCase() === "REJECTED";

                          return (
                            <div
                              key={item.id}
                              style={{
                                background: "rgba(255, 255, 255, 0.02)",
                                padding: "18px 20px",
                                borderRadius: "10px",
                                border: `1px solid ${isHigh ? "rgba(239, 68, 68, 0.3)" : "rgba(255, 255, 255, 0.07)"}`,
                              }}
                            >
                              {/* Header */}
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", marginBottom: "10px" }}>
                                <div>
                                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                                    <span className={`badge ${item.workstream === 'legal' ? 'badge-legal' : item.workstream === 'cross_domain' ? 'badge-cross' : 'badge-financial'}`}>
                                      {item.workstream.toUpperCase()}
                                    </span>
                                    <span className={`badge ${isHigh ? 'badge-high' : isMed ? 'badge-medium' : 'badge-verified'}`}>
                                      {item.risk_severity.toUpperCase()} RISK
                                    </span>
                                    <span className={`badge ${isApproved ? 'badge-verified' : isRejected ? 'badge-high' : 'badge-medium'}`}>
                                      {item.status.toUpperCase()}
                                    </span>
                                  </div>
                                  <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc", margin: 0 }}>
                                    {item.title}
                                  </h4>
                                </div>
                              </div>

                              {/* Details */}
                              <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: "1.6", marginBottom: "8px" }}>
                                <strong>Issue:</strong> {item.issue}
                              </p>

                              {item.why_it_matters && (
                                <p style={{ fontSize: "12.5px", color: "#94a3b8", lineHeight: "1.5", marginBottom: "6px" }}>
                                  <strong style={{ color: "#cbd5e1" }}>Commercial Impact:</strong> {item.why_it_matters}
                                </p>
                              )}

                              {item.recommended_action && (
                                <p style={{ fontSize: "12.5px", color: "#94a3b8", lineHeight: "1.5", marginBottom: "10px" }}>
                                  <strong style={{ color: "#818cf8" }}>Recommended Action:</strong> {item.recommended_action}
                                </p>
                              )}

                              {/* Attached Evidence Drawer */}
                              {item.evidence && item.evidence.length > 0 && (
                                <div style={{ marginTop: "12px", paddingTop: "10px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                                  <div style={{ fontSize: "11px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", marginBottom: "6px" }}>
                                    Source Evidence ({item.evidence.length})
                                  </div>
                                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "8px" }}>
                                    {item.evidence.map((ev, eIdx) => (
                                      <div key={eIdx} style={{ background: "#080c14", padding: "8px 12px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.05)", fontSize: "11.5px" }}>
                                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                                          <strong style={{ color: "#38bdf8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                            {ev.document_name}
                                          </strong>
                                          <span className={`badge ${ev.validation_status === 'VERIFIED' ? 'badge-verified' : 'badge-high'}`} style={{ fontSize: "9px", padding: "1px 5px" }}>
                                            {ev.validation_status}
                                          </span>
                                        </div>
                                        <p style={{ margin: 0, color: "#94a3b8", fontStyle: "italic", fontSize: "11px" }}>
                                          Page {ev.page_number || "-"}: &ldquo;{(ev.quoted_text || ev.extracted_value || "Claim").slice(0, 120)}...&rdquo;
                                        </p>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Reviewer notes */}
                              {item.reviews && item.reviews.length > 0 && (
                                <div style={{ marginTop: "10px", fontSize: "11.5px", color: "#64748b" }}>
                                  Reviewer: <strong style={{ color: "#94a3b8" }}>{item.reviews[item.reviews.length - 1].reviewer_name || "Lead Reviewer"}</strong> • Action: <strong>{item.reviews[item.reviews.length - 1].action}</strong> • &ldquo;{item.reviews[item.reviews.length - 1].comments}&rdquo;
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>

                {/* 5. Outstanding Items (Requests / Tasks) */}
                {reportData.outstanding_items && reportData.outstanding_items.length > 0 && (
                  <div className="glass-card" style={{ padding: "18px 22px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                      <ListTodo size={16} color="#fbbf24" />
                      <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>
                        Outstanding Information Requests & Action Items ({reportData.outstanding_items.length})
                      </h3>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {reportData.outstanding_items.map((oi, oIdx) => (
                        <div key={oIdx} style={{ background: "rgba(255,255,255,0.02)", padding: "10px 14px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div>
                            <div style={{ fontSize: "12.5px", fontWeight: "600", color: "#f8fafc" }}>{oi.title}</div>
                            <div style={{ fontSize: "11.5px", color: "#94a3b8" }}>{oi.description}</div>
                          </div>
                          <div style={{ display: "flex", gap: "6px" }}>
                            <span className="badge badge-medium" style={{ fontSize: "10px" }}>{oi.priority.toUpperCase()}</span>
                            <span className="badge badge-legal" style={{ fontSize: "10px" }}>{oi.status}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 6. Limitations & Audit Disclaimers */}
                <div className="glass-card" style={{ padding: "18px 22px", background: "rgba(10, 14, 26, 0.7)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                    <CheckCircle2 size={16} color="#94a3b8" />
                    <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#cbd5e1" }}>Diligence Limitations & Audit Disclaimers</h3>
                  </div>
                  <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12px", color: "#94a3b8", lineHeight: "1.7" }}>
                    {reportData.limitations.map((lim, lIdx) => (
                      <li key={lIdx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Global Modals */}
        {/* Project Create / Edit Modal */}
            {projectModalOpen && (
              <div className="modal-overlay" onClick={() => setProjectModalOpen(false)}>
                <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "560px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <Briefcase size={18} color="#818cf8" />
                      <h3 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>
                        {projectModalMode === "create" ? "Create Due Diligence Project" : "Edit Project & Workstreams"}
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => setProjectModalOpen(false)}
                      style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "16px" }}
                    >
                      ✕
                    </button>
                  </div>
                  <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "16px" }}>
                    Configure the target company entity, deal profile, diligence timeline, and active specialist workstreams.
                  </p>

                  {projectFormError && (
                    <div style={{ marginBottom: "14px", padding: "10px 14px", borderRadius: "8px", background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#fca5a5", fontSize: "12.5px" }}>
                      {projectFormError}
                    </div>
                  )}

                  <form onSubmit={handleSaveProject} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                      <div>
                        <label style={{ fontSize: "11.5px", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "4px" }}>
                          Project Name *
                        </label>
                        <input
                          type="text"
                          required
                          value={projectForm.name}
                          onChange={(e) => setProjectForm({ ...projectForm, name: e.target.value })}
                          placeholder="e.g. Project AsterNova Due Diligence"
                          className="input-field"
                          style={{ width: "100%", fontSize: "13px" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "11.5px", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "4px" }}>
                          Target Company *
                        </label>
                        <input
                          type="text"
                          required
                          value={projectForm.target_company}
                          onChange={(e) => setProjectForm({ ...projectForm, target_company: e.target.value })}
                          placeholder="e.g. AsterNova Technologies Pvt. Ltd."
                          className="input-field"
                          style={{ width: "100%", fontSize: "13px" }}
                        />
                      </div>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
                      <div>
                        <label style={{ fontSize: "11.5px", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "4px" }}>
                          Deal Type
                        </label>
                        <select
                          value={projectForm.deal_type}
                          onChange={(e) => setProjectForm({ ...projectForm, deal_type: e.target.value })}
                          className="input-field"
                          style={{ width: "100%", fontSize: "12px" }}
                        >
                          <option value="Acquisition">Acquisition</option>
                          <option value="Merger">Merger</option>
                          <option value="Minority Investment">Minority Investment</option>
                          <option value="Joint Venture">Joint Venture</option>
                          <option value="Asset Purchase">Asset Purchase</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ fontSize: "11.5px", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "4px" }}>
                          Industry Sector
                        </label>
                        <input
                          type="text"
                          value={projectForm.industry}
                          onChange={(e) => setProjectForm({ ...projectForm, industry: e.target.value })}
                          placeholder="e.g. SaaS / FinTech"
                          className="input-field"
                          style={{ width: "100%", fontSize: "12px" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "11.5px", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "4px" }}>
                          Diligence Period
                        </label>
                        <input
                          type="text"
                          value={projectForm.diligence_period}
                          onChange={(e) => setProjectForm({ ...projectForm, diligence_period: e.target.value })}
                          placeholder="e.g. Q1 2026"
                          className="input-field"
                          style={{ width: "100%", fontSize: "12px" }}
                        />
                      </div>
                    </div>

                    <div>
                      <label style={{ fontSize: "11.5px", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "4px" }}>
                        Project Description
                      </label>
                      <textarea
                        rows={2}
                        value={projectForm.description}
                        onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })}
                        placeholder="Key transaction context, deal drivers, or critical areas of concern..."
                        className="textarea-field"
                        style={{ width: "100%", fontSize: "12.5px" }}
                      />
                    </div>

                    <div style={{ background: "rgba(255,255,255,0.02)", padding: "12px 16px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.06)" }}>
                      <div style={{ fontSize: "12px", fontWeight: "700", color: "#f8fafc", marginBottom: "8px" }}>
                        Initial Workstreams Selection
                      </div>
                      <div style={{ display: "flex", gap: "20px" }}>
                        <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#34d399", cursor: "pointer" }}>
                          <input
                            type="checkbox"
                            checked={projectForm.financial}
                            onChange={(e) => setProjectForm({ ...projectForm, financial: e.target.checked })}
                          />
                          Financial Due Diligence
                        </label>
                        <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#38bdf8", cursor: "pointer" }}>
                          <input
                            type="checkbox"
                            checked={projectForm.legal}
                            onChange={(e) => setProjectForm({ ...projectForm, legal: e.target.checked })}
                          />
                          Legal Due Diligence
                        </label>
                      </div>
                      <p style={{ fontSize: "11px", color: "#64748b", marginTop: "6px" }}>
                        Cross-Domain analysis automatically runs when multiple workstreams are enabled.
                      </p>
                    </div>

                    <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => setProjectModalOpen(false)}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="btn btn-primary btn-sm"
                        disabled={savingProject}
                      >
                        {savingProject ? "Saving..." : projectModalMode === "create" ? "Create Project" : "Save Changes"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* Scope & Key Questions Modal */}
            {scopeModalOpen && (
              <div className="modal-overlay" onClick={() => setScopeModalOpen(false)}>
                <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "580px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <Settings size={18} color="#818cf8" />
                      <h3 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>
                        Configure Scope: {activeScopeWs.toUpperCase()} Workstream
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => setScopeModalOpen(false)}
                      style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "16px" }}
                    >
                      ✕
                    </button>
                  </div>

                  {/* Workstream Switcher Tabs */}
                  <div style={{ display: "flex", gap: "8px", marginBottom: "14px", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "10px" }}>
                    <button
                      type="button"
                      className={`btn btn-sm ${activeScopeWs === "financial" ? "btn-primary" : "btn-secondary"}`}
                      onClick={() => openScopeModal("financial")}
                    >
                      Financial Scope
                    </button>
                    <button
                      type="button"
                      className={`btn btn-sm ${activeScopeWs === "legal" ? "btn-primary" : "btn-secondary"}`}
                      onClick={() => openScopeModal("legal")}
                    >
                      Legal Scope
                    </button>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    <div>
                      <label style={{ fontSize: "12px", fontWeight: "700", color: "#cbd5e1", display: "block", marginBottom: "4px" }}>
                        Key Investigation Questions (one per line)
                      </label>
                      <p style={{ fontSize: "11.5px", color: "#94a3b8", marginBottom: "6px" }}>
                        Specific hypotheses or queries the specialist agent must investigate.
                      </p>
                      <textarea
                        rows={5}
                        value={scopeKeyQuestions}
                        onChange={(e) => setScopeKeyQuestions(e.target.value)}
                        placeholder={`e.g.\nValidate FY 2025 revenue and EBITDA against ledger data\nVerify debt covenants and credit facility limits\nAssess customer concentration risks`}
                        className="textarea-field"
                        style={{ width: "100%", fontSize: "12.5px" }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: "700", color: "#cbd5e1", display: "block", marginBottom: "4px" }}>
                        Requested Review Areas (one per line)
                      </label>
                      <p style={{ fontSize: "11.5px", color: "#94a3b8", marginBottom: "6px" }}>
                        Core diligence categories relevant to this workstream.
                      </p>
                      <textarea
                        rows={3}
                        value={scopeReviewAreas}
                        onChange={(e) => setScopeReviewAreas(e.target.value)}
                        placeholder={`e.g.\nRevenue Recognition\nOperating Leases & Liabilities\nContingent Liabilities`}
                        className="textarea-field"
                        style={{ width: "100%", fontSize: "12.5px" }}
                      />
                    </div>

                    <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "4px" }}>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => setScopeModalOpen(false)}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={handleSaveScope}
                        disabled={savingScope}
                      >
                        {savingScope ? "Saving..." : "Save Scope Configuration"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
      </main>
    </div>
  );
}
