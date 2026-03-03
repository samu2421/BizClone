"""
Business data loader - loads business_data.json into the database.
"""
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.db import crud

logger = get_logger(__name__)


def load_business_data(db: Session) -> dict:
    """
    Load business data from JSON file into the database.
    
    Returns:
        dict: Summary of loaded data
    """
    # Get the path to business_data.json
    json_path = Path(__file__).parent / "business_data.json"
    
    if not json_path.exists():
        logger.error("business_data_not_found", path=str(json_path))
        raise FileNotFoundError(f"Business data file not found: {json_path}")
    
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info("business_data_loaded_from_file", path=str(json_path))
    
    # Track what was loaded
    summary = {
        "services": 0,
        "policies": 0,
        "faqs": 0
    }
    
    # Load services
    if "services" in data:
        for service_key, service_data in data["services"].items():
            # Convert service_key to a readable name
            name = service_key.replace("_", " ").title()
            
            crud.create_or_update_service(
                db=db,
                service_key=service_key,
                name=name,
                description=service_data.get("description", ""),
                price=service_data.get("price", "")
            )
            summary["services"] += 1
        
        logger.info("services_loaded", count=summary["services"])
    
    # Load policies
    if "policies" in data:
        for policy_key, policy_content in data["policies"].items():
            # Convert policy_key to a readable name
            name = policy_key.replace("_", " ").title()
            
            crud.create_or_update_policy(
                db=db,
                policy_key=policy_key,
                name=name,
                content=policy_content
            )
            summary["policies"] += 1
        
        logger.info("policies_loaded", count=summary["policies"])
    
    # Load FAQs
    if "faqs" in data:
        for faq_item in data["faqs"]:
            crud.create_or_update_faq(
                db=db,
                question=faq_item.get("q", ""),
                answer=faq_item.get("a", "")
            )
            summary["faqs"] += 1
        
        logger.info("faqs_loaded", count=summary["faqs"])
    
    logger.info(
        "business_data_load_complete",
        services=summary["services"],
        policies=summary["policies"],
        faqs=summary["faqs"]
    )
    
    return summary


def get_business_context(db: Session) -> str:
    """
    Get formatted business context for AI prompts.
    
    Returns:
        str: Formatted business context including services, policies, and FAQs
    """
    context_parts = []
    
    # Get services
    services = crud.get_all_services(db)
    if services:
        context_parts.append("**Available Services:**")
        for service in services:
            context_parts.append(
                f"- {service.name}: {service.description} (Price: {service.price})"
            )
        context_parts.append("")
    
    # Get policies
    policies = crud.get_all_policies(db)
    if policies:
        context_parts.append("**Business Policies:**")
        for policy in policies:
            context_parts.append(f"- {policy.name}: {policy.content}")
        context_parts.append("")
    
    # Get FAQs (limit to first 20 for context size)
    faqs = crud.get_all_faqs(db)
    if faqs:
        context_parts.append("**Frequently Asked Questions:**")
        for faq in faqs[:20]:
            context_parts.append(f"Q: {faq.question}")
            context_parts.append(f"A: {faq.answer}")
            context_parts.append("")
    
    return "\n".join(context_parts)


def search_business_knowledge(db: Session, query: str) -> str:
    """
    Search business knowledge base for relevant information.
    
    Args:
        db: Database session
        query: Search query
        
    Returns:
        str: Formatted search results
    """
    results = []
    
    # Search FAQs
    faqs = crud.search_faqs(db, query, limit=5)
    if faqs:
        results.append("**Relevant FAQs:**")
        for faq in faqs:
            results.append(f"Q: {faq.question}")
            results.append(f"A: {faq.answer}")
            results.append("")
    
    return "\n".join(results) if results else "No relevant information found."

