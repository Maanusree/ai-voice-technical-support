"""
Escalation Tickets API Routes
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Form
from ..services.escalation_service import escalation_service
from ..models.ticket import TicketStatus

router = APIRouter(prefix="/api/tickets", tags=["Escalation Tickets"])


@router.get("")
async def list_tickets():
    """List all created Tier-2 escalation tickets."""
    tickets = escalation_service.list_tickets()
    return {"tickets": tickets}


@router.get("/{ticket_id}")
async def get_ticket_details(ticket_id: str):
    """Retrieve full details of an escalation ticket including caller transcript."""
    ticket = escalation_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, status: TicketStatus = Form(...)):
    """Update resolution status of a support ticket."""
    ticket = escalation_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = status
    escalation_service.save_ticket(ticket)
    return {"status": "updated", "ticket": ticket}
