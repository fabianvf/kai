import re
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kai.analyzer import AnalyzerLSP
from kai.cache import JSONCacheWithTrace
from kai.jsonrpc.util import AutoAbsPathExists
from kai.kai_config import KaiConfigModels
from kai.llm_interfacing.model_provider import ModelProvider
from kai.logging.logging import get_logger
from kai.reactive_codeplanner.agent.analyzer_fix.agent import AnalyzerAgent

# Import Kai core components
from kai.reactive_codeplanner.task_manager.task_manager import TaskManager
from kai.reactive_codeplanner.task_runner.analyzer_lsp.task_runner import (
    AnalyzerTaskRunner,
)
from kai.reactive_codeplanner.vfs.git_vfs import RepoContextManager

# Initialize FastAPI MCP Server
app = FastAPI()
log = get_logger("kai_mcp_server")


# ---------------------- CONFIG MODEL ----------------------
class MCPInitConfig(BaseModel):
    """Configuration model for initializing Kai's MCP server"""

    root_path: str
    model_provider: KaiConfigModels
    log_config: Dict[str, Any]
    demo_mode: bool = False
    cache_dir: str = "/tmp/kai_cache"
    trace_enabled: bool = False
    enable_reflection: bool = True

    analyzer_lsp_rpc_path: str
    analyzer_lsp_lsp_path: str
    analyzer_lsp_rules_paths: List[str]
    analyzer_lsp_java_bundle_paths: List[str]
    analyzer_lsp_dep_labels_path: Optional[str] = None
    analyzer_lsp_excluded_paths: Optional[List[str]] = None


# ---------------------- GLOBAL APP STATE ----------------------
class MCPState:
    """Global state for MCP server"""

    initialized = False
    config = None
    task_manager = None
    repo_manager = None
    analyzer = None


state = MCPState()


# ---------------------- INITIALIZATION ENDPOINT ----------------------
@app.post("/mcp/initialize")
async def initialize(config: MCPInitConfig):
    """Initialize Kai's MCP server with the given configuration"""
    global state

    if state.initialized:
        raise HTTPException(status_code=400, detail="Server already initialized")

    try:
        log.info("Initializing MCP Server...")
        state.config = config

        # 1️⃣ SETUP CACHE
        cache = JSONCacheWithTrace(
            cache_dir=config.cache_dir,
            model_id="",
            enable_trace=config.trace_enabled,
            trace_dir=Path(config.log_config["log_dir_path"]) / "traces",
            fail_on_cache_mismatch=False,
        )
        model_provider = ModelProvider(config.model_provider, config.demo_mode, cache)
        cache.model_id = re.sub(r"[\.:\\/]", "_", model_provider.model_id)

        # 2️⃣ INITIALIZE ANALYZER
        state.analyzer = AnalyzerLSP(
            analyzer_lsp_server_binary=config.analyzer_lsp_rpc_path,
            repo_directory=config.root_path,
            rules=config.analyzer_lsp_rules_paths,
            java_bundles=config.analyzer_lsp_java_bundle_paths,
            analyzer_lsp_path=config.analyzer_lsp_lsp_path,
            dep_open_source_labels_path=config.analyzer_lsp_dep_labels_path or Path(),
            excluded_paths=config.analyzer_lsp_excluded_paths,
        )

        # 3️⃣ SETUP REPO MANAGER
        state.repo_manager = RepoContextManager(
            project_root=config.root_path,
            reflection_agent=None,  # Optionally enable ReflectionAgent
        )

        # 4️⃣ SETUP TASK MANAGER
        state.task_manager = TaskManager(
            config=None,  # Assume tasks are dynamically configured
            rcm=state.repo_manager,
            validators=[],  # Validators can be added here
            task_runners=[AnalyzerTaskRunner(AnalyzerAgent(model_provider))],
        )

        state.initialized = True
        return {"status": "Kai MCP Server initialized successfully"}

    except Exception as e:
        log.error(f"Initialization failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------- TASK MANAGEMENT ENDPOINTS ----------------------
@app.get("/mcp/tasks")
async def get_tasks():
    """Retrieve available tasks from Kai's task manager"""
    if not state.initialized:
        raise HTTPException(status_code=400, detail="Server not initialized")

    try:
        tasks = state.task_manager.priority_queue.all_tasks()
        return [{"id": task.id, "description": str(task)} for task in tasks]
    except Exception as e:
        log.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/execute-task")
async def execute_task(task_id: str):
    """Execute a task using Kai's agentic system"""
    if not state.initialized:
        raise HTTPException(status_code=400, detail="Server not initialized")

    try:
        task = state.task_manager.get_task_by_id(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        result = state.task_manager.execute_task(task)
        return {"status": "Task executed", "result": str(result)}

    except Exception as e:
        log.error(f"Task execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/task/{task_id}/solution")
async def get_solution(task_id: str):
    """Retrieve the AI-generated solution for a task"""
    if not state.initialized:
        raise HTTPException(status_code=400, detail="Server not initialized")

    try:
        task = state.task_manager.get_task_by_id(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Assuming `task.result` contains the suggested fix
        return {"solution": str(task.result)}

    except Exception as e:
        log.error(f"Error retrieving solution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/task/{task_id}/revalidate")
async def revalidate_task(task_id: str):
    """Re-run analysis to confirm the fix"""
    if not state.initialized:
        raise HTTPException(status_code=400, detail="Server not initialized")

    try:
        state.task_manager.revalidate_task(task_id)
        return {"status": "Revalidated"}

    except Exception as e:
        log.error(f"Revalidation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------- SERVER RUNNER ----------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
