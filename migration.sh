#!/bin/bash
# simple_migrate.sh

echo "📁 Creating minimal organization..."

# Create new folders
mkdir -p src/core src/services src/api

# Move core business logic
echo "Moving core files..."
mv src/bse.py src/core/
mv src/maf.py src/core/
mv src/agk.py src/core/
mv src/sol.py src/core/
mv src/meme_gen.py src/core/

# Move services
echo "Moving service files..."
mv src/config_manager.py src/services/
mv src/audit_logger.py src/services/
mv src/environment_manager.py src/services/
mv src/encryption_utils.py src/services/
mv src/token_tracking.py src/services/

# Move API files
echo "Moving API files..."
mv src/webhook_server.py src/api/
mv src/get_token.py src/api/

# Keep analytics folder as-is (already organized)

echo "✅ Simple migration completed!"
