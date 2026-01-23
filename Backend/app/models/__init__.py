"""
Database models for NBA Bets application
"""

# Core models
# User legacy model removed - use UserAccount instead
from .user_accounts import UserAccount, Client, Administrator, Operator  # Normalized user models
from .two_factor import UserTwoFactor  # Two-Factor Authentication
from .user_session import UserSession  # User sessions tracking
from .team import Team
from .game import Game
# Bet legacy model removed - use EspnBet from espn_bet instead
from .transaction import Transaction
from .team_stats import TeamStatsGame

# Normalized ESPN models (3FN)
from .espn_bet import (
    BetType as EspnBetType,
    BetStatus as EspnBetStatus,
    Bet as EspnBet,
    BetSelection,
    BetResult,
    GameOdds
)

# RBAC models (RF-01)
from .role import Role
from .permission import Permission
from .role_permission import RolePermission
from .user_role import UserRole

# Idempotency and requests (RF-02, RF-03)
from .idempotency_key import IdempotencyKey
from .request import Request, RequestStatus

# Predictions (RF-06, RF-07)
from .model_version import ModelVersion
from .prediction import Prediction

# Providers (RF-05, RF-18)
from .provider import Provider
from .provider_endpoint import ProviderEndpoint

# Snapshots (RF-07)
from .odds_snapshot import OddsSnapshot
from .odds_line import OddsLine

# Audit and messaging (RF-08, RF-10)
from .audit_log import AuditLog
from .outbox import Outbox

from app.core.database import SysBase, EspnBase, Base

__all__ = [
    "Base",
    "SysBase",
    "EspnBase",
    # Core models
    # "User" legacy removed - use "UserAccount" instead
    "UserAccount",  # Normalized user account base
    "Client",  # Normalized client (replaces "usuario")
    "Administrator",  # Normalized administrator
    "Operator",  # Normalized operator
    "UserTwoFactor",  # Two-Factor Authentication
    "UserSession",  # User sessions tracking
    "Team", 
    "Game",
    # "Bet" legacy removed - use "EspnBet" instead
    "Transaction",
    "TeamStatsGame",
    # Normalized ESPN models (3FN)
    "EspnBetType",
    "EspnBetStatus",
    "EspnBet",
    "BetSelection",
    "BetResult",
    "GameOdds",
    # RBAC models
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    # Idempotency and requests
    "IdempotencyKey",
    "Request",
    "RequestStatus",
    # Predictions
    "ModelVersion",
    "Prediction",
    # Providers
    "Provider",
    "ProviderEndpoint",
    # Snapshots
    "OddsSnapshot",
    "OddsLine",
    # Audit and messaging
    "AuditLog",
    "Outbox",
]
