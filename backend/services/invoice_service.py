import urllib
from typing import List, Dict, Any, Optional, cast
from datetime import datetime
from uuid import UUID, uuid4
import urllib.parse
import httpx
from datetime import datetime
from models.listing import ListingCreate, ListingInDB, ListingUpdate
from models.invoice import Invoice
from database import mongodb
from services.nostr_service import nostr_service

from services.nwc import processNWCstring, makeInvoice, getInfo, checkInvoice, tryToPayInvoice, didPaymentSucceed




class InvoiceService:
    """Service for handling LN invoices"""

    collection_name = "invoices"
    async def get_nwc_info(self,nwc_string: str) -> Any:
        try:
            return processNWCstring(nwc_string)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing NWC string: {e}")

    async def get_lnurl_info(self, lightning_address: str) -> dict:
        """Resolve a Nostr Lightning Address to its LNURL-pay endpoint"""
        try:
            username, domain = lightning_address.split("@")
            url = f"https://{domain}/.well-known/lnurlp/{username}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            raise RuntimeError(f"Failed to resolve LNURL: {e}")

    async def create_invoice(self, lightning_address: str, amount_sats: int, comment: str = "") -> dict:
        """Request an invoice from a Nostr Lightning Address"""
        try:
            lnurl_info = await self.get_lnurl_info(lightning_address)
            callback_url = lnurl_info["callback"]
            params = {
                "amount": amount_sats * 1000, #in milisats
            }
            if comment:
                params["comment"] = comment
            full_url = f"{callback_url}?{urllib.parse.urlencode(params)}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(full_url)
                resp.raise_for_status()
                response_data = resp.json()

                invoice_data = {
                    "type": "zap",
                    "invoice": response_data.get("pr", ""),
                    "payment_hash": response_data.get("payment_hash", ""),
                    "amount": amount_sats,
                    "fees_paid": 0,
                    "description": comment,
                    "created_at": datetime.now().timestamp(),
                }

                return invoice_data

        except Exception as e:
            raise RuntimeError(f"Failed to create an invoice: {e}")

    async def check_invoice_status(self,nwc_string, invoicestr) -> Invoice:
        try:
            nwc_info = processNWCstring(nwc_string)
            nwc_info['relay'] = urllib.parse.unquote(nwc_info['relay'])
            result = checkInvoice(nwc_info, invoicestr)
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to check invoice: {e}")

    async def try_to_pay_invoice(self,nwc_buyer_string, invoicestr) -> Invoice:
        try:
            nwc_info = processNWCstring(nwc_buyer_string)
            nwc_info['relay'] = urllib.parse.unquote(nwc_info['relay'])
            result = tryToPayInvoice(nwc_info, invoicestr)
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to try to pay invoice: {e}")

    async def check_payment(self, nwc_buyer_string, invoicestr) -> bool:
        try:
            result = await self.check_invoice_status(nwc_buyer_string, invoicestr)
            return (
                    result and
                    "result" in result and
                    result["result"].get("settled_at") is not None
            )
        except Exception as e:
            raise RuntimeError(f"Failed to check payment: {e}")


invoice_service = InvoiceService()