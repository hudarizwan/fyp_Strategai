# Backend Scripts

## Analytics model version activation

Use `python backend/scripts/set_active_analytics_model_version.py --id <uuid>` or `--version-tag <tag>` to switch the active analytics model version.

This script connects directly to PostgreSQL so the deactivate + activate switch happens in a single transaction.
The Supabase dashboard is not part of the supported workflow because it cannot guarantee that ordering.

## MCB threshold management

Use `python backend/scripts/set_mcb_category_threshold.py --category <category> --threshold <0-1> [--reason <text>]` to change the approval threshold for one category.

This script also connects directly to PostgreSQL so the threshold update and audit row are written in one transaction.
Direct table edits are not part of the supported workflow. The fixed actor value used for now is `system:threshold-script`.
