# Human-in-the-Loop UI Implementation Plan

## Overview

Add a web-based UI to the Claude Clinical Bridge that allows human reviewers to:
- View and edit agent outputs after each phase
- Approve/reject phase results before advancing to the next phase
- Track workflow progress in real-time
- Submit final approved documentation for billing

**Tech Stack**: React + TypeScript (Vite), FastAPI, PostgreSQL, JWT auth

---

## Architecture Changes

### Current Flow (CLI)
```
main.py → coordinator.process_note() → runs all 5 phases → returns final WorkflowState
```

### New Flow (HITL UI)
```
Frontend → API → coordinator.run_phase(workflow_id, phase_name) →
  → saves to DB →
  → frontend polls status →
  → human reviews →
  → frontend calls advance_phase() →
  → repeat
```

---

## Milestone 1: Database Schema & Models

### 1.1 Database Tables

**`workflows` table**:
```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by_user_id INTEGER REFERENCES users(id),

    status VARCHAR(20) NOT NULL, -- pending, in_progress, needs_review, completed, failed
    current_phase VARCHAR(20), -- documentation, coding, compliance, prior_auth, quality_assurance, done

    raw_note TEXT NOT NULL,
    patient_id VARCHAR(100),
    payer VARCHAR(100),
    procedure VARCHAR(100),
    skip_prior_auth BOOLEAN DEFAULT FALSE,

    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_created_by ON workflows(created_by_user_id);
CREATE INDEX idx_workflows_created_at ON workflows(created_at DESC);
```

**`phase_results` table**:
```sql
CREATE TABLE phase_results (
    id SERIAL PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    phase_name VARCHAR(20) NOT NULL, -- documentation, coding, compliance, prior_auth, quality_assurance

    status VARCHAR(20) NOT NULL, -- pending, running, completed, failed, skipped
    content TEXT, -- JSON blob from agent
    edited_content TEXT, -- Human-edited version (if modified)
    error TEXT,

    input_tokens INTEGER,
    output_tokens INTEGER,
    duration_seconds FLOAT,

    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by_user_id INTEGER REFERENCES users(id),

    UNIQUE(workflow_id, phase_name)
);

CREATE INDEX idx_phase_results_workflow ON phase_results(workflow_id);
```

**`users` table** (simple auth):
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'reviewer', -- reviewer, admin
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Default user: admin / admin (change in production!)
INSERT INTO users (username, hashed_password, full_name, role)
VALUES ('admin', '$2b$12$...', 'Admin User', 'admin');
```

**`audit_log` table** (use existing AuditLogger):
- Already implemented in `src/python/security/audit_logger.py`
- Writes to JSON log files currently
- Enhance to also write to PostgreSQL for queryability

### 1.2 SQLAlchemy Models

**File**: `src/python/api/models.py`

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from src.python.utils.database import Base

class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"

class PhaseStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))

    status = Column(SQLEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.PENDING)
    current_phase = Column(String(20))

    raw_note = Column(Text, nullable=False)
    patient_id = Column(String(100))
    payer = Column(String(100))
    procedure = Column(String(100))
    skip_prior_auth = Column(Boolean, default=False)

    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    phase_results = relationship("PhaseResult", back_populates="workflow", cascade="all, delete-orphan")
    created_by = relationship("User")

class PhaseResult(Base):
    __tablename__ = "phase_results"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    phase_name = Column(String(20), nullable=False)

    status = Column(SQLEnum(PhaseStatus), nullable=False, default=PhaseStatus.PENDING)
    content = Column(Text)
    edited_content = Column(Text)
    error = Column(Text)

    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    duration_seconds = Column(Float)

    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    workflow = relationship("Workflow", back_populates="phase_results")
    reviewed_by = relationship("User")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="reviewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 1.3 Database Setup

**File**: `src/python/utils/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.python.utils.config import settings

SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**File**: `scripts/init_db.py` (database migration)

```python
from src.python.utils.database import Base, engine
from src.python.api.models import Workflow, PhaseResult, User

# Create all tables
Base.metadata.create_all(bind=engine)
```

---

## Milestone 2: Refactor Coordinator for Step-by-Step Execution

### 2.1 Changes to `src/python/orchestration/coordinator.py`

Current `process_note()` runs all phases in sequence. Need to add:

**New method**: `run_single_phase(workflow_id: UUID, phase_name: str, db: Session) -> PhaseResult`

```python
async def run_single_phase(
    self,
    workflow_id: UUID,
    phase_name: str,
    db: Session
) -> PhaseResult:
    """Run a single phase of the pipeline and save to database."""
    from src.python.api.models import Workflow as WorkflowModel, PhaseResult as PhaseResultModel

    # Load workflow from DB
    workflow_db = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
    if not workflow_db:
        raise ValueError(f"Workflow {workflow_id} not found")

    # Get phase results so far
    phase_results = {pr.phase_name: pr for pr in workflow_db.phase_results}

    # Determine which agent to run
    if phase_name == "documentation":
        agent = self.doc_agent
        inputs = {"raw_note": workflow_db.raw_note, "context": {}}
        method = agent.structure_note

    elif phase_name == "coding":
        doc_result = phase_results.get("documentation")
        if not doc_result or doc_result.status != PhaseStatus.COMPLETED:
            raise ValueError("Documentation phase must be completed first")

        agent = self.coding_agent
        # Use edited_content if human edited it, otherwise use original content
        doc_content = doc_result.edited_content or doc_result.content
        inputs = {"documentation": doc_content, "context": {}}
        method = agent.suggest_codes

    # ... similar for compliance, prior_auth, quality_assurance ...

    # Create phase result entry
    phase_result_db = PhaseResultModel(
        workflow_id=workflow_id,
        phase_name=phase_name,
        status=PhaseStatus.RUNNING,
        started_at=datetime.utcnow()
    )
    db.add(phase_result_db)
    db.commit()

    # Run the agent
    start = time.monotonic()
    try:
        result = await method(**inputs)
        duration = time.monotonic() - start

        # Update phase result
        phase_result_db.status = PhaseStatus.COMPLETED
        phase_result_db.content = result.get("content", "")
        phase_result_db.input_tokens = result.get("usage", {}).get("input_tokens", 0)
        phase_result_db.output_tokens = result.get("usage", {}).get("output_tokens", 0)
        phase_result_db.duration_seconds = duration
        phase_result_db.completed_at = datetime.utcnow()

        # Update workflow totals
        workflow_db.total_input_tokens += phase_result_db.input_tokens or 0
        workflow_db.total_output_tokens += phase_result_db.output_tokens or 0

    except Exception as e:
        phase_result_db.status = PhaseStatus.FAILED
        phase_result_db.error = str(e)
        phase_result_db.completed_at = datetime.utcnow()
        workflow_db.status = WorkflowStatus.FAILED

    db.commit()
    db.refresh(phase_result_db)

    return phase_result_db
```

### 2.2 Changes to `src/python/orchestration/state.py`

Add serialization methods to `WorkflowState`:

```python
def to_dict(self) -> dict:
    """Serialize to JSON-compatible dict."""
    return {
        "workflow_id": str(self.workflow_id),
        "status": self.status,
        "raw_note": self.raw_note,
        "patient_id": self.patient_id,
        "payer": self.payer,
        "skip_prior_auth": self.skip_prior_auth,
        "total_tokens": self.total_tokens,
        "started_at": self.started_at,
        "completed_at": self.completed_at,
        "documentation": self.documentation.to_dict() if self.documentation else None,
        "coding": self.coding.to_dict() if self.coding else None,
        "compliance": self.compliance.to_dict() if self.compliance else None,
        "prior_auth": self.prior_auth.to_dict() if self.prior_auth else None,
        "quality_assurance": self.quality_assurance.to_dict() if self.quality_assurance else None,
    }

@classmethod
def from_db(cls, workflow_db, phase_results_db):
    """Load from database models."""
    # Convert DB models to WorkflowState dataclass
    ...
```

---

## Milestone 3: FastAPI Backend

### 3.1 API Structure

```
src/python/api/
├── __init__.py
├── main.py              # FastAPI app
├── models.py            # SQLAlchemy models (from M1.2)
├── schemas.py           # Pydantic request/response schemas
├── auth.py              # JWT authentication
├── dependencies.py      # get_db, get_current_user
└── routers/
    ├── __init__.py
    ├── auth.py          # POST /auth/login, /auth/me
    ├── workflows.py     # CRUD for workflows
    └── phases.py        # Phase execution & editing
```

### 3.2 Key Endpoints

**File**: `src/python/api/routers/workflows.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from src.python.api import schemas, models
from src.python.api.dependencies import get_db, get_current_user

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

@router.post("/", response_model=schemas.WorkflowResponse)
async def create_workflow(
    request: schemas.WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new workflow from a clinical note."""
    workflow = models.Workflow(
        raw_note=request.raw_note,
        patient_id=request.patient_id,
        payer=request.payer,
        procedure=request.procedure,
        skip_prior_auth=request.skip_prior_auth,
        created_by_user_id=current_user.id,
        status=models.WorkflowStatus.PENDING,
        current_phase="documentation"
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    # Create pending phase result entries
    phases = ["documentation", "coding", "compliance", "quality_assurance"]
    if request.payer and request.procedure and not request.skip_prior_auth:
        phases.insert(3, "prior_auth")

    for phase_name in phases:
        phase_result = models.PhaseResult(
            workflow_id=workflow.id,
            phase_name=phase_name,
            status=models.PhaseStatus.PENDING
        )
        db.add(phase_result)

    db.commit()

    return workflow

@router.get("/", response_model=List[schemas.WorkflowSummary])
async def list_workflows(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List workflows (optionally filtered by status)."""
    query = db.query(models.Workflow)
    if status:
        query = query.filter(models.Workflow.status == status)

    workflows = query.order_by(models.Workflow.created_at.desc()).offset(skip).limit(limit).all()
    return workflows

@router.get("/{workflow_id}", response_model=schemas.WorkflowDetail)
async def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get workflow with all phase results."""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return workflow

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a workflow (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db.delete(workflow)
    db.commit()

    return {"message": "Workflow deleted"}
```

**File**: `src/python/api/routers/phases.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from src.python.api import schemas, models
from src.python.api.dependencies import get_db, get_current_user
from src.python.orchestration.coordinator import ClinicalPipelineCoordinator
from src.python.utils.config import settings
import anthropic

router = APIRouter(prefix="/api/phases", tags=["phases"])

@router.post("/{workflow_id}/run/{phase_name}")
async def run_phase(
    workflow_id: UUID,
    phase_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Run a single phase in the background."""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Validate phase name
    valid_phases = ["documentation", "coding", "compliance", "prior_auth", "quality_assurance"]
    if phase_name not in valid_phases:
        raise HTTPException(status_code=400, detail=f"Invalid phase: {phase_name}")

    # Start phase execution in background
    background_tasks.add_task(
        _run_phase_task,
        workflow_id=workflow_id,
        phase_name=phase_name
    )

    return {"message": f"Phase {phase_name} started", "workflow_id": str(workflow_id)}

async def _run_phase_task(workflow_id: UUID, phase_name: str):
    """Background task to run a phase."""
    from src.python.utils.database import SessionLocal

    db = SessionLocal()
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        coordinator = ClinicalPipelineCoordinator(client=client)

        await coordinator.run_single_phase(
            workflow_id=workflow_id,
            phase_name=phase_name,
            db=db
        )
    finally:
        db.close()

@router.patch("/{workflow_id}/phases/{phase_name}")
async def edit_phase_content(
    workflow_id: UUID,
    phase_name: str,
    request: schemas.PhaseContentEdit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Edit phase content (human review)."""
    phase_result = db.query(models.PhaseResult).filter(
        models.PhaseResult.workflow_id == workflow_id,
        models.PhaseResult.phase_name == phase_name
    ).first()

    if not phase_result:
        raise HTTPException(status_code=404, detail="Phase result not found")

    # Update edited content
    phase_result.edited_content = request.edited_content
    phase_result.reviewed_at = datetime.utcnow()
    phase_result.reviewed_by_user_id = current_user.id

    db.commit()

    # Log audit event
    from src.python.security.audit_logger import AuditLogger, AuditAction
    audit = AuditLogger()
    audit.log(
        action=AuditAction.UPDATE,
        user_id=str(current_user.id),
        resource_type="phase_result",
        resource_id=str(phase_result.id),
        details={"phase": phase_name, "edited": True}
    )

    return {"message": "Phase content updated"}

@router.post("/{workflow_id}/phases/{phase_name}/approve")
async def approve_phase(
    workflow_id: UUID,
    phase_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Approve phase and advance workflow to next phase."""
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    phase_result = db.query(models.PhaseResult).filter(
        models.PhaseResult.workflow_id == workflow_id,
        models.PhaseResult.phase_name == phase_name
    ).first()

    if not phase_result or phase_result.status != models.PhaseStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Phase must be completed before approval")

    # Mark as reviewed
    phase_result.reviewed_at = datetime.utcnow()
    phase_result.reviewed_by_user_id = current_user.id

    # Advance to next phase
    phase_order = ["documentation", "coding", "compliance", "prior_auth", "quality_assurance"]
    current_idx = phase_order.index(phase_name)

    if current_idx < len(phase_order) - 1:
        next_phase = phase_order[current_idx + 1]

        # Skip prior_auth if not needed
        if next_phase == "prior_auth" and (workflow.skip_prior_auth or not workflow.payer or not workflow.procedure):
            next_phase = "quality_assurance"

        workflow.current_phase = next_phase
        workflow.status = models.WorkflowStatus.NEEDS_REVIEW
    else:
        # Final phase approved
        workflow.current_phase = "done"
        workflow.status = models.WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.utcnow()

    db.commit()

    # Audit log
    from src.python.security.audit_logger import AuditLogger, AuditAction
    audit = AuditLogger()
    audit.log(
        action=AuditAction.QA_REVIEW if phase_name == "quality_assurance" else AuditAction.UPDATE,
        user_id=str(current_user.id),
        resource_type="workflow",
        resource_id=str(workflow_id),
        details={"phase": phase_name, "approved": True, "next_phase": workflow.current_phase}
    )

    return {"message": f"Phase {phase_name} approved", "next_phase": workflow.current_phase}
```

**File**: `src/python/api/routers/auth.py`

```python
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.python.api import models, schemas
from src.python.api.dependencies import get_db
from src.python.utils.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with username/password, returns JWT token."""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")

    access_token = create_access_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(
    current_user: models.User = Depends(get_current_user)
):
    """Get current user info from token."""
    return current_user
```

### 3.3 Pydantic Schemas

**File**: `src/python/api/schemas.py`

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class WorkflowCreate(BaseModel):
    raw_note: str
    patient_id: Optional[str] = None
    payer: Optional[str] = None
    procedure: Optional[str] = None
    skip_prior_auth: bool = False

class PhaseResultResponse(BaseModel):
    id: int
    phase_name: str
    status: str
    content: Optional[str]
    edited_content: Optional[str]
    error: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    duration_seconds: Optional[float]
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True

class WorkflowSummary(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    current_phase: Optional[str]
    patient_id: Optional[str]
    payer: Optional[str]

    class Config:
        from_attributes = True

class WorkflowDetail(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    status: str
    current_phase: Optional[str]
    raw_note: str
    patient_id: Optional[str]
    payer: Optional[str]
    procedure: Optional[str]
    skip_prior_auth: bool
    total_input_tokens: int
    total_output_tokens: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    phase_results: List[PhaseResultResponse]

    class Config:
        from_attributes = True

class PhaseContentEdit(BaseModel):
    edited_content: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str

    class Config:
        from_attributes = True
```

---

## Milestone 4: React Frontend

### 4.1 Frontend Structure

```
src/typescript/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api/
    │   ├── client.ts           # Axios instance with auth
    │   ├── auth.ts             # Login, logout, getMe
    │   ├── workflows.ts        # CRUD for workflows
    │   └── phases.ts           # Phase run, edit, approve
    ├── components/
    │   ├── Layout.tsx          # App shell with nav
    │   ├── ProtectedRoute.tsx  # Auth guard
    │   ├── PhaseCard.tsx       # Single phase result card
    │   ├── PhaseEditor.tsx     # JSON editor for phase content
    │   └── LoadingSpinner.tsx
    ├── pages/
    │   ├── Login.tsx           # /login
    │   ├── Dashboard.tsx       # /dashboard - workflow list
    │   ├── WorkflowDetail.tsx  # /workflows/:id - phase tabs
    │   └── CreateWorkflow.tsx  # /workflows/new
    ├── hooks/
    │   ├── useAuth.ts          # Auth context
    │   └── useWorkflowPolling.ts  # Poll phase status
    └── types/
        └── api.ts              # TypeScript interfaces matching schemas
```

### 4.2 Key Components

**File**: `src/typescript/src/pages/WorkflowDetail.tsx`

```tsx
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getWorkflow, runPhase, approvePhase } from '../api/workflows';
import { WorkflowDetail as WorkflowType, PhaseResult } from '../types/api';
import PhaseCard from '../components/PhaseCard';

export default function WorkflowDetail() {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<WorkflowType | null>(null);
  const [loading, setLoading] = useState(true);

  // Poll for updates every 3 seconds
  useEffect(() => {
    const fetchWorkflow = async () => {
      const data = await getWorkflow(id!);
      setWorkflow(data);
      setLoading(false);
    };

    fetchWorkflow();
    const interval = setInterval(fetchWorkflow, 3000);

    return () => clearInterval(interval);
  }, [id]);

  const handleRunPhase = async (phaseName: string) => {
    await runPhase(id!, phaseName);
    // Will be picked up by polling
  };

  const handleApprovePhase = async (phaseName: string) => {
    await approvePhase(id!, phaseName);
    // Refresh immediately
    const data = await getWorkflow(id!);
    setWorkflow(data);
  };

  if (loading) return <div>Loading...</div>;
  if (!workflow) return <div>Workflow not found</div>;

  const phaseOrder = ['documentation', 'coding', 'compliance', 'prior_auth', 'quality_assurance'];
  const phaseResults = workflow.phase_results.reduce((acc, pr) => {
    acc[pr.phase_name] = pr;
    return acc;
  }, {} as Record<string, PhaseResult>);

  return (
    <div className="workflow-detail">
      <header>
        <h1>Workflow {workflow.id}</h1>
        <span className={`status-badge ${workflow.status}`}>{workflow.status}</span>
      </header>

      <section className="raw-note">
        <h2>Clinical Note</h2>
        <pre>{workflow.raw_note}</pre>
      </section>

      <section className="phases">
        {phaseOrder.map(phaseName => {
          const phase = phaseResults[phaseName];
          if (!phase) return null;

          return (
            <PhaseCard
              key={phaseName}
              phase={phase}
              workflowId={id!}
              onRun={() => handleRunPhase(phaseName)}
              onApprove={() => handleApprovePhase(phaseName)}
              isCurrentPhase={workflow.current_phase === phaseName}
            />
          );
        })}
      </section>
    </div>
  );
}
```

**File**: `src/typescript/src/components/PhaseCard.tsx`

```tsx
import { useState } from 'react';
import { PhaseResult } from '../types/api';
import PhaseEditor from './PhaseEditor';

interface PhaseCardProps {
  phase: PhaseResult;
  workflowId: string;
  onRun: () => void;
  onApprove: () => void;
  isCurrentPhase: boolean;
}

export default function PhaseCard({ phase, workflowId, onRun, onApprove, isCurrentPhase }: PhaseCardProps) {
  const [editing, setEditing] = useState(false);

  const canRun = phase.status === 'pending' && isCurrentPhase;
  const canApprove = phase.status === 'completed' && isCurrentPhase;
  const isRunning = phase.status === 'running';

  return (
    <div className={`phase-card ${phase.status} ${isCurrentPhase ? 'current' : ''}`}>
      <header>
        <h3>{phase.phase_name}</h3>
        <span className="status-badge">{phase.status}</span>
      </header>

      {phase.error && (
        <div className="error-box">
          <strong>Error:</strong> {phase.error}
        </div>
      )}

      {phase.content && (
        <div className="phase-content">
          {editing ? (
            <PhaseEditor
              workflowId={workflowId}
              phaseName={phase.phase_name}
              initialContent={phase.edited_content || phase.content}
              onSave={() => setEditing(false)}
              onCancel={() => setEditing(false)}
            />
          ) : (
            <>
              <pre>{phase.edited_content || phase.content}</pre>
              {canApprove && (
                <button onClick={() => setEditing(true)}>Edit</button>
              )}
            </>
          )}
        </div>
      )}

      <footer>
        {canRun && <button onClick={onRun}>Run Phase</button>}
        {isRunning && <div className="spinner">Running...</div>}
        {canApprove && (
          <>
            <button onClick={onApprove} className="approve-btn">Approve & Continue</button>
          </>
        )}

        {phase.duration_seconds && (
          <span className="meta">Duration: {phase.duration_seconds.toFixed(1)}s</span>
        )}
        {phase.input_tokens && (
          <span className="meta">Tokens: {phase.input_tokens + phase.output_tokens}</span>
        )}
      </footer>
    </div>
  );
}
```

---

## Milestone 5: Integration & Testing

### 5.1 Backend Server Startup

**File**: `src/python/api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.python.api.routers import auth, workflows, phases
from src.python.utils.database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Claude Clinical Bridge API", version="1.0.0")

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(workflows.router)
app.include_router(phases.router)

@app.get("/")
def root():
    return {"message": "Claude Clinical Bridge API"}
```

**Run command**:
```bash
uvicorn src.python.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.2 Frontend Dev Server

**File**: `src/typescript/package.json`

```json
{
  "name": "claude-clinical-bridge-ui",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

**Run command**:
```bash
cd src/typescript
npm install
npm run dev
```

### 5.3 Docker Compose Update

**File**: `docker-compose.yml` (add API service)

```yaml
services:
  # ... existing qdrant, postgres, redis ...

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=postgresql://clinicaluser:clinicalpass@postgres:5432/clinicaldb
    depends_on:
      - postgres
      - redis
      - qdrant
    volumes:
      - ./src:/app/src
    command: uvicorn src.python.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Implementation Order

1. **Milestone 1** (2-3 hours):
   - Create database models (`src/python/api/models.py`)
   - Add database util (`src/python/utils/database.py`)
   - Run migration script to create tables
   - Create default admin user

2. **Milestone 2** (2-3 hours):
   - Refactor `coordinator.py` to add `run_single_phase()` method
   - Update `state.py` with serialization methods
   - Test phase-by-phase execution manually

3. **Milestone 3** (3-4 hours):
   - Build FastAPI app structure
   - Implement auth endpoints with JWT
   - Implement workflow CRUD endpoints
   - Implement phase execution endpoints
   - Test all endpoints with curl/Postman

4. **Milestone 4** (4-6 hours):
   - Set up React + Vite + TypeScript
   - Build auth pages (login, protected routes)
   - Build dashboard (workflow list)
   - Build workflow detail page with phase cards
   - Build phase editor component
   - Add polling for real-time updates

5. **Milestone 5** (1-2 hours):
   - Integration testing (frontend → API → agents → DB)
   - Update Docker Compose
   - Update README with UI setup instructions
   - Create default admin user seed script

**Total estimated time**: 12-18 hours

---

## Security Checklist

- [ ] JWT tokens expire after 24 hours
- [ ] Passwords hashed with bcrypt (12 rounds)
- [ ] PHI redaction on all logs via `PHIRedactor`
- [ ] Audit logging for all human review actions
- [ ] CORS restricted to frontend origin only
- [ ] HTTPS in production (nginx reverse proxy)
- [ ] SECRET_KEY is 32+ chars and random
- [ ] Database credentials in `.env` (not committed)
- [ ] Default admin password must be changed on first login

---

## Future Enhancements

- WebSocket for real-time phase execution updates (instead of polling)
- Role-based permissions (reviewer can only approve, admin can delete)
- Workflow assignment (assign to specific users)
- Comments/annotations on phase results
- Workflow templates for common scenarios
- Bulk workflow processing
- Export to PDF/Word for submission
