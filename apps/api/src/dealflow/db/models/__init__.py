"""DealFlow V2 ORM model registry — imported by Alembic env.py to populate Base.metadata."""

from .ai_operations import AiAction, Appointment, HumanApproval, LeadAssignment, PromptVersion, Task
from .audit_knowledge import ActivityTimeline, AuditLog, KnowledgeChunk, KnowledgeDocument
from .conversations import Conversation, Message, MessageDeliveryAttempt
from .integrations import CrmMapping, IntegrationConnection, SyncLog
from .lead_ingestion import (
    Contact,
    ContactMergeEvent,
    ContactPoint,
    DedupeCandidate,
    IngestionEvent,
    Lead,
    LeadNextAction,
    LeadPreference,
    LeadScore,
    LeadSource,
)
from .sla_consent import (
    ConsentRecord,
    LeadSlaResult,
    MessagingPolicySettings,
    OptOutRecord,
    TenantSlaSettings,
)
from .tenant_auth import AgentProfile, Role, Tenant, TenantInvitation, TenantMembership, User
from .workflow import OutboxEvent

__all__ = [
    # Tenant / Auth
    "Tenant",
    "User",
    "TenantMembership",
    "Role",
    "AgentProfile",
    "TenantInvitation",
    # Lead Ingestion
    "LeadSource",
    "IngestionEvent",
    "Contact",
    "ContactPoint",
    "Lead",
    "LeadPreference",
    "LeadScore",
    "LeadNextAction",
    "DedupeCandidate",
    "ContactMergeEvent",
    # Conversations
    "Conversation",
    "Message",
    "MessageDeliveryAttempt",
    # AI
    "PromptVersion",
    "AiAction",
    "HumanApproval",
    # Operations
    "LeadAssignment",
    "Task",
    "Appointment",
    # Integrations
    "IntegrationConnection",
    "CrmMapping",
    "SyncLog",
    # SLA / Consent
    "TenantSlaSettings",
    "LeadSlaResult",
    "MessagingPolicySettings",
    "ConsentRecord",
    "OptOutRecord",
    # Workflow
    "OutboxEvent",
    # Audit / Timeline
    "AuditLog",
    "ActivityTimeline",
    # Knowledge Base
    "KnowledgeDocument",
    "KnowledgeChunk",
]
