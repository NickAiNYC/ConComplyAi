#!/usr/bin/env python3
"""
Demo: Scout → Guard → Fixer Triple Handshake
Demonstrates the complete remediation loop with automatic Fixer trigger

SHOWCASES:
1. Scout discovers NYC construction opportunity
2. Guard validates COI and detects deficiencies  
3. WorkflowManager automatically triggers Fixer
4. Fixer drafts professional remediation email
5. Complete audit chain verification
6. Cost efficiency tracking (< $0.005/doc target)
"""
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.core.workflow_manager import create_workflow_manager


def main():
    print("=" * 80)
    print("SCOUT → GUARD → FIXER TRIPLE HANDSHAKE DEMO")
    print("=" * 80)
    print()
    print("This demo shows ConComplyAi's autonomous remediation capability:")
    print("  • Scout finds opportunity")
    print("  • Guard detects compliance gaps")
    print("  • Fixer auto-drafts remediation email")
    print()
    
    # Initialize workflow manager
    workflow_manager = create_workflow_manager(
        base_upload_url="https://concomplai.com/upload"
    )
    
    # Run complete pipeline
    print("🔄 Running Scout → Guard → Fixer pipeline...")
    print("-" * 80)
    
    result = workflow_manager.run_full_pipeline(
        scout_result=None,  # Will run Scout
        opportunity_index=0,  # Use first opportunity
        coi_pdf_path=None    # Will use mock path
    )
    
    if not result["success"]:
        print(f"❌ Pipeline failed: {result.get('error')}")
        return
    
    # Display results
    print()
    summary = workflow_manager.get_pipeline_summary(result)
    print(summary)
    
    # Show Fixer email if generated
    fixer_result = result.get("fixer_result")
    if fixer_result:
        print()
        print("=" * 80)
        print("FIXER EMAIL DRAFT")
        print("=" * 80)
        email_draft = fixer_result["email_draft"]
        print(f"\nFrom: ConComplyAi Compliance Team")
        print(f"To: {result['guard_result']['compliance_result'].document_id} Broker")
        print(f"Subject: {email_draft.subject}")
        print(f"Priority: {email_draft.priority}")
        print()
        print("-" * 80)
        print(email_draft.body)
        print("-" * 80)
        print()
        print(f"✅ Email draft ready for broker outreach")
        print(f"📊 Cited {len(email_draft.cited_regulations)} NYC regulations")
        print(f"🔗 Correction link: {email_draft.correction_link}")
    
    # Investor pitch summary
    print()
    print("=" * 80)
    print("INVESTOR VALUE PROPOSITION")
    print("=" * 80)
    print()
    print("ConComplyAi doesn't just 'find problems'—it 'initiates solutions' autonomously.")
    print()
    print("✅ DEMONSTRATED CAPABILITIES:")
    print(f"   • Scout discovered {len(result['scout_result']['opportunities'])} opportunities in 24 hours")
    print(f"   • Guard validated compliance in {result['guard_result']['duration_ms']}ms")
    print(f"   • Fixer drafted professional remediation email automatically")
    print(f"   • Complete audit chain maintained (verified: {'✅' if result['chain_valid'] else '❌'})")
    print(f"   • Cost efficiency: ${result['total_cost_usd']:.6f} (target: $0.005)")
    print()
    print("💰 COST EFFICIENCY:")
    total_cost = result['total_cost_usd']
    target_cost = 0.005
    if total_cost < target_cost:
        savings = target_cost - total_cost
        print(f"   ✅ Under target by ${savings:.6f} ({(savings/target_cost)*100:.1f}%)")
    else:
        overage = total_cost - target_cost
        print(f"   ⚠️  Over target by ${overage:.6f} ({(overage/target_cost)*100:.1f}%)")
    
    print()
    print("🎯 KEY DIFFERENTIATOR:")
    print("   Traditional systems stop at 'rejected'.")
    print("   ConComplyAi automatically initiates broker outreach with:")
    print("     - Specific regulatory citations (RCNY 101-08, SCA specs)")
    print("     - High-EQ construction professional tone")
    print("     - One-click correction upload link")
    print("     - Cryptographic audit trail for compliance")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
