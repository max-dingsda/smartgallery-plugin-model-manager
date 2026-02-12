# smartgallery-plugin-model-manager
# Backend logic for the Model Manager plugin
# Provides helper functions and API routes for model scanning and management

import os
import hashlib
import json
import sqlite3
import time
from flask import request, jsonify, current_app
from .config import BASE_MODELS_PATH, MODEL_SUBFOLDERS, MODEL_EXTENSIONS


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def get_db_connection():
    """Get shared database connection via Flask app config."""
    db_path = current_app.config.get('MM_DATABASE_FILE', './gallery_cache.sqlite')
    conn = sqlite3.connect(db_path, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    return conn


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def fast_model_id(path):
    """Fast unique ID based on head+tail bytes (AutoV2 style)"""
    try:
        with open(path, "rb") as f:
            f.seek(0x100000)
            head = f.read(0x10000)
            f.seek(-0x10000, os.SEEK_END)
            tail = f.read(0x10000)
        return hashlib.sha256(head + tail).hexdigest()[:16]
    except:
        return hashlib.md5(path.encode()).hexdigest()[:16]


def calculate_full_sha256(filepath):
    """Calculate full SHA256 hash (for CivitAI compatibility)"""
    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Hash calculation error for {filepath}: {e}")
        return None


def extract_safetensors_metadata(path):
    """Extract trigger words and tags from safetensors header"""
    try:
        with open(path, 'rb') as f:
            header_size_bytes = f.read(8)
            if len(header_size_bytes) < 8:
                return None, None
            header_size = int.from_bytes(header_size_bytes, 'little')
            if header_size > 100_000_000:
                return None, None
            header_json = f.read(header_size).decode('utf-8', errors='ignore')
            metadata = json.loads(header_json)

            trigger = None
            tags = None

            if '__metadata__' in metadata:
                meta = metadata['__metadata__']
                if 'ss_tag_frequency' in meta:
                    try:
                        tag_data = json.loads(meta['ss_tag_frequency'])
                        all_tags = []
                        for dataset_tags in tag_data.values():
                            all_tags.extend(dataset_tags.keys())
                        tags = ', '.join(sorted(set(all_tags))[:50])
                    except: pass

                trigger_keys = ['ss_trigger_word', 'activation_text', 'trigger_word']
                for key in trigger_keys:
                    if key in meta and meta[key]:
                        trigger = meta[key]
                        break

            return trigger, tags
    except:
        return None, None


def detect_architecture_from_keys(metadata_keys):
    """Detect model architecture from safetensors keys"""
    keys_lower = [k.lower() for k in metadata_keys]
    keys_str = ' '.join(keys_lower)

    if any('cascade' in k or 'effnet' in k for k in keys_lower):
        return 'Stable Cascade'
    if any('pony' in k for k in keys_lower):
        return 'Pony'
    if 'model.diffusion_model.joint_blocks.0.x_block.attn.qkv.weight' in metadata_keys:
        return 'Flux'
    if any('double_blocks' in k or 'single_blocks' in k for k in keys_lower):
        return 'Flux'
    if any('down_blocks.2.attentions.1.transformer_blocks.9' in k for k in metadata_keys):
        return 'SDXL'
    if any('cond_stage_model.transformer.text_model.embeddings' in k for k in metadata_keys):
        return 'SD 1.x/2.x'

    return 'Unknown'


def pick_effective_value(civitai_value, local_value, legacy_value=None):
    """Pick effective display value with CivitAI priority and local fallback."""
    if civitai_value:
        return civitai_value
    if local_value:
        return local_value
    return legacy_value


def scan_models(force_rescan=False):
    """Scan model folders and return list of models (incremental)"""
    from .config import get_models_path
    # Use the active app DB so settings saved via /settings are respected
    db_path = current_app.config.get('MM_DATABASE_FILE', './gallery_cache.sqlite')
    base_path = get_models_path(db_path)
    print(f"🔍 DEBUG: Scanning models in: {base_path}")
    print(f"🔍 DEBUG: Path exists: {os.path.exists(base_path)}")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        found_models = []
        scanned_paths = set()
        current_time = int(time.time())

        for kind, folders in MODEL_SUBFOLDERS.items():
            for folder in folders:
                folder_path = os.path.join(base_path, folder)
                if not os.path.exists(folder_path):
                    continue

                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if not any(file.lower().endswith(ext) for ext in MODEL_EXTENSIONS):
                            continue

                        full_path = os.path.join(root, file)
                        scanned_paths.add(full_path)

                        try:
                            file_stat = os.stat(full_path)
                            file_mtime = int(file_stat.st_mtime)
                            file_size = file_stat.st_size
                            local_name = os.path.splitext(file)[0]

                            model_id = fast_model_id(full_path)

                            cursor.execute("""
                                SELECT
                                    mtime, hash, name, trigger, tags,
                                    name_local, name_civitai, version_civitai, type_civitai,
                                    base_model_civitai, creator_civitai, license_civitai, civitai_model_url,
                                    civitai_checked_at,
                                    trigger_local, trigger_civitai,
                                    tags_local, tags_civitai
                                FROM mm_models
                                WHERE id = ?
                            """, (model_id,))
                            existing = cursor.fetchone()

                            if existing and not force_rescan:
                                if existing[0] == file_mtime:
                                    existing_hash = existing[1]
                                    legacy_name, legacy_trigger, legacy_tags = existing[2], existing[3], existing[4]
                                    name_local, name_civitai = existing[5], existing[6]
                                    version_civitai = existing[7]
                                    type_civitai = existing[8]
                                    base_model_civitai, creator_civitai, license_civitai, civitai_model_url = existing[9], existing[10], existing[11], existing[12]
                                    civitai_checked_at = existing[13]
                                    trigger_local, trigger_civitai = existing[14], existing[15]
                                    tags_local, tags_civitai = existing[16], existing[17]

                                    # Backfill local columns for older rows if needed.
                                    if not name_local:
                                        name_local = local_name
                                        cursor.execute("UPDATE mm_models SET name_local = ? WHERE id = ?", (name_local, model_id))

                                    effective_name = pick_effective_value(name_civitai, name_local, legacy_name)
                                    effective_trigger = pick_effective_value(trigger_civitai, trigger_local, legacy_trigger)
                                    effective_tags = pick_effective_value(tags_civitai, tags_local, legacy_tags)

                                    found_models.append({
                                        'id': model_id,
                                        'type': kind,
                                        'name': effective_name,
                                        'path': full_path,
                                        'size': file_size,
                                        'hash': existing_hash,
                                        'mtime': file_mtime,
                                        'trigger': effective_trigger,
                                        'tags': effective_tags,
                                        'name_local': name_local,
                                        'name_civitai': name_civitai,
                                        'version_name': version_civitai,
                                        'type_civitai': type_civitai,
                                        'base_model': base_model_civitai,
                                        'creator': creator_civitai,
                                        'license': license_civitai,
                                        'civitai_model_url': civitai_model_url,
                                        'civitai_checked_at': civitai_checked_at,
                                        'trigger_local': trigger_local,
                                        'trigger_civitai': trigger_civitai,
                                        'tags_local': tags_local,
                                        'tags_civitai': tags_civitai
                                    })
                                    continue

                            trigger_local, tags_local = extract_safetensors_metadata(full_path)
                            name_civitai = None
                            version_civitai = None
                            type_civitai = None
                            base_model_civitai = None
                            creator_civitai = None
                            license_civitai = None
                            civitai_model_url = None
                            civitai_checked_at = None
                            trigger_civitai = None
                            tags_civitai = None
                            existing_hash = None

                            if existing:
                                name_civitai = existing[6]
                                version_civitai = existing[7]
                                type_civitai = existing[8]
                                base_model_civitai = existing[9]
                                creator_civitai = existing[10]
                                license_civitai = existing[11]
                                civitai_model_url = existing[12]
                                civitai_checked_at = existing[13]
                                trigger_civitai = existing[15]
                                tags_civitai = existing[17]
                                existing_hash = existing[1]

                            effective_name = pick_effective_value(name_civitai, local_name)
                            effective_trigger = pick_effective_value(trigger_civitai, trigger_local)
                            effective_tags = pick_effective_value(tags_civitai, tags_local)

                            cursor.execute("""
                                INSERT OR REPLACE INTO mm_models (
                                    id, type, name, path, size, hash, mtime, scanned_at, trigger, tags,
                                    name_local, name_civitai, version_civitai, type_civitai, base_model_civitai, creator_civitai, license_civitai, civitai_model_url,
                                    civitai_checked_at,
                                    trigger_local, trigger_civitai, tags_local, tags_civitai
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                model_id,
                                kind,
                                effective_name,
                                full_path,
                                file_size,
                                existing_hash,
                                file_mtime,
                                current_time,
                                effective_trigger,
                                effective_tags,
                                local_name,
                                name_civitai,
                                version_civitai,
                                type_civitai,
                                base_model_civitai,
                                creator_civitai,
                                license_civitai,
                                civitai_model_url,
                                civitai_checked_at,
                                trigger_local,
                                trigger_civitai,
                                tags_local,
                                tags_civitai
                            ))

                            found_models.append({
                                'id': model_id,
                                'type': kind,
                                'name': effective_name,
                                'path': full_path,
                                'size': file_size,
                                'hash': existing_hash,
                                'mtime': file_mtime,
                                'trigger': effective_trigger,
                                'tags': effective_tags,
                                'name_local': local_name,
                                'name_civitai': name_civitai,
                                'version_name': version_civitai,
                                'type_civitai': type_civitai,
                                'base_model': base_model_civitai,
                                'creator': creator_civitai,
                                'license': license_civitai,
                                'civitai_model_url': civitai_model_url,
                                'civitai_checked_at': civitai_checked_at,
                                'trigger_local': trigger_local,
                                'trigger_civitai': trigger_civitai,
                                'tags_local': tags_local,
                                'tags_civitai': tags_civitai
                            })

                        except Exception as e:
                            print(f"Error scanning {file}: {e}")
                            continue

        # Remove models from DB that no longer exist on disk
        cursor.execute("SELECT path FROM mm_models")
        db_paths = {row[0] for row in cursor.fetchall()}
        paths_to_delete = db_paths - scanned_paths

        if paths_to_delete:
            for path in paths_to_delete:
                cursor.execute("DELETE FROM mm_models WHERE path = ?", (path,))

        conn.commit()

    print(f"Model scan complete: {len(found_models)} models found")
    return found_models


# ---------------------------------------------------------------------------
# API Routes (Blueprint)
# ---------------------------------------------------------------------------

def register_routes(bp):
    """Register all Model Manager API routes on the given Blueprint."""

    @bp.route('/')
    def index():
        """Serve the Model Manager HTML page."""
        from flask import render_template
        return render_template('model_manager.html')

    @bp.route('/scan', methods=['POST'])
    def api_scan_models():
        """Scan models (incremental, only new/changed)"""
        try:
            force = request.json.get('force', False) if request.is_json else False
            models = scan_models(force_rescan=force)
            return jsonify({
                'status': 'success',
                'count': len(models),
                'models': models
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @bp.route('/list', methods=['GET'])
    def api_list_models():
        """Load models from DB (auto-scans on first call)"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Check if DB is empty
                cursor.execute("SELECT COUNT(*) FROM mm_models")
                count = cursor.fetchone()[0]

            # First call? Then scan!
            if count == 0:
                print("Models DB is empty - starting initial scan...")
                models = scan_models(force_rescan=False)
                return jsonify({
                    'status': 'success',
                    'count': len(models),
                    'models': models,
                    'initial_scan': True
                })

            # DB has data - load from DB
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        id, type, name, path, size, hash, mtime, trigger, tags,
                        name_local, name_civitai, version_civitai, type_civitai, base_model_civitai, creator_civitai, license_civitai, civitai_model_url,
                        civitai_checked_at,
                        trigger_local, trigger_civitai, tags_local, tags_civitai
                    FROM mm_models
                    ORDER BY type, name COLLATE NOCASE
                """)

                models = []
                for row in cursor.fetchall():
                    models.append({
                        'id': row[0],
                        'type': row[1],
                        'name': pick_effective_value(row[10], row[9], row[2]),
                        'path': row[3],
                        'size': row[4],
                        'hash': row[5],
                        'mtime': row[6],
                        'trigger': pick_effective_value(row[19], row[18], row[7]),
                        'tags': pick_effective_value(row[21], row[20], row[8]),
                        'name_local': row[9],
                        'name_civitai': row[10],
                        'version_name': row[11],
                        'type_civitai': row[12],
                        'base_model': row[13],
                        'creator': row[14],
                        'license': row[15],
                        'civitai_model_url': row[16],
                        'civitai_checked_at': row[17],
                        'trigger_local': row[18],
                        'trigger_civitai': row[19],
                        'tags_local': row[20],
                        'tags_civitai': row[21]
                    })

            return jsonify({
                'status': 'success',
                'count': len(models),
                'models': models
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @bp.route('/update-civitai', methods=['POST'])
    def api_update_civitai_metadata():
        """Update model metadata from CivitAI"""
        try:
            data = request.json
            if not data or 'updates' not in data:
                return jsonify({'status': 'error', 'message': 'Missing updates data'}), 400

            with get_db_connection() as conn:
                cursor = conn.cursor()

                updated_count = 0
                for update in data['updates']:
                    model_id = update.get('modelId')
                    civitai_data = update.get('civitaiData', {})
                    civitai_not_found = bool(update.get('civitaiNotFound', False))

                    if not model_id:
                        continue

                    civitai_checked_at = int(time.time())

                    if civitai_not_found:
                        cursor.execute("""
                            UPDATE mm_models
                            SET civitai_checked_at = ?
                            WHERE id = ?
                        """, (civitai_checked_at, model_id))
                        if cursor.rowcount > 0:
                            updated_count += 1
                        continue

                    model_name_civitai = civitai_data.get('name', '') or None
                    version_civitai = civitai_data.get('versionName', '') or None
                    type_civitai = civitai_data.get('modelType', '') or None
                    base_model_civitai = civitai_data.get('baseModel', '') or None
                    creator_civitai = civitai_data.get('creatorUsername', '') or civitai_data.get('creator', '') or None
                    license_civitai = civitai_data.get('license', '') or None
                    civitai_model_url = civitai_data.get('civitaiModelUrl', '') or None
                    trigger_civitai = civitai_data.get('triggerWords', '') or civitai_data.get('tags', '') or None
                    tags_civitai = civitai_data.get('modelTags', '') or None

                    # Keep legacy effective columns in sync for compatibility.
                    cursor.execute("""
                        SELECT name_local, trigger_local, tags_local, name, trigger, tags
                        FROM mm_models
                        WHERE id = ?
                    """, (model_id,))
                    existing = cursor.fetchone()
                    if not existing:
                        continue

                    local_name, local_trigger, local_tags = existing[0], existing[1], existing[2]
                    legacy_name, legacy_trigger, legacy_tags = existing[3], existing[4], existing[5]

                    effective_name = pick_effective_value(model_name_civitai, local_name, legacy_name)
                    effective_trigger = pick_effective_value(trigger_civitai, local_trigger, legacy_trigger)
                    effective_tags = pick_effective_value(tags_civitai, local_tags, legacy_tags)

                    print(
                        f"Updating model {model_id}: "
                        f"name_civitai='{model_name_civitai}', version_civitai='{version_civitai}', type_civitai='{type_civitai}', "
                        f"base_model_civitai='{base_model_civitai}', creator_civitai='{creator_civitai}', "
                        f"license_civitai='{license_civitai}', civitai_model_url='{civitai_model_url}', "
                        f"trigger_civitai='{trigger_civitai}', tags_civitai='{tags_civitai}'"
                    )

                    cursor.execute("""
                        UPDATE mm_models
                        SET
                            name_civitai = ?,
                            version_civitai = ?,
                            type_civitai = ?,
                            base_model_civitai = ?,
                            creator_civitai = ?,
                            license_civitai = ?,
                            civitai_model_url = ?,
                            civitai_checked_at = ?,
                            trigger_civitai = ?,
                            tags_civitai = ?,
                            name = ?,
                            trigger = ?,
                            tags = ?
                        WHERE id = ?
                    """, (
                        model_name_civitai,
                        version_civitai,
                        type_civitai,
                        base_model_civitai,
                        creator_civitai,
                        license_civitai,
                        civitai_model_url,
                        civitai_checked_at,
                        trigger_civitai,
                        tags_civitai,
                        effective_name,
                        effective_trigger,
                        effective_tags,
                        model_id
                    ))

                    if cursor.rowcount > 0:
                        updated_count += 1

                conn.commit()

            return jsonify({
                'status': 'success',
                'updated': updated_count,
                'message': f'Updated {updated_count} models'
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @bp.route('/calculate-full-hash', methods=['POST'])
    def api_calculate_full_hash():
        """Calculate full SHA256 hash for selected models (for CivitAI compatibility)"""
        try:
            data = request.json
            if not data or 'modelIds' not in data:
                return jsonify({'status': 'error', 'message': 'Missing modelIds'}), 400

            model_ids = data['modelIds']

            with get_db_connection() as conn:
                cursor = conn.cursor()

                results = []
                for model_id in model_ids:
                    # Get model path from DB
                    cursor.execute("SELECT path FROM mm_models WHERE id = ?", (model_id,))
                    row = cursor.fetchone()

                    if not row:
                        results.append({'modelId': model_id, 'status': 'error', 'message': 'Model not found'})
                        continue

                    filepath = row[0]

                    if not os.path.exists(filepath):
                        results.append({'modelId': model_id, 'status': 'error', 'message': 'File not found'})
                        continue

                    # Calculate full hash
                    print(f"Calculating full SHA256 for: {os.path.basename(filepath)}")
                    full_hash = calculate_full_sha256(filepath)

                    if full_hash:
                        # Update DB with full hash
                        cursor.execute("UPDATE mm_models SET hash = ? WHERE id = ?", (full_hash, model_id))
                        results.append({'modelId': model_id, 'status': 'success', 'hash': full_hash})
                        print(f"  -> Full hash: {full_hash[:16]}...")
                    else:
                        results.append({'modelId': model_id, 'status': 'error', 'message': 'Hash calculation failed'})

                conn.commit()

            return jsonify({
                'status': 'success',
                'results': results
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @bp.route('/settings', methods=['GET'])
    def api_get_settings():
        """Get current settings."""
        from .config import get_models_path

        with get_db_connection() as conn:
            models_path = get_models_path(conn.execute("PRAGMA database_list").fetchone()[2])

            return jsonify({
                'status': 'success',
                'settings': {
                    'models_path': models_path
                }
            })

    @bp.route('/settings', methods=['POST'])
    def api_save_settings():
        """Save settings to database."""
        data = request.json
        models_path = data.get('models_path', '').strip()

        if not models_path:
            return jsonify({'status': 'error', 'message': 'Models path cannot be empty'}), 400

        # Validate path exists
        if not os.path.isdir(models_path):
            return jsonify({'status': 'error', 'message': f'Directory not found: {models_path}'}), 400

        # Save to database and clear cached models so the next /list
        # call triggers a fresh scan of the new directory.
        with get_db_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO mm_settings (key, value)
                VALUES ('models_path', ?)
            ''', (models_path,))
            conn.execute('DELETE FROM mm_models')
            conn.commit()

        return jsonify({'status': 'success', 'message': 'Settings saved successfully'})

    @bp.route('/detect-paths', methods=['GET'])
    def api_detect_paths():
        """Auto-detect potential model directories on all platforms."""
        import platform
        import string
        from .config import MODEL_SUBFOLDERS, MODEL_EXTENSIONS

        candidates = set()

        # Always check relative to CWD
        candidates.add(os.path.abspath('./models'))
        candidates.add(os.path.abspath('../models'))

        if platform.system() == 'Windows':
            # Scan all available drive letters
            for letter in string.ascii_uppercase:
                drive = f'{letter}:\\'
                if not os.path.exists(drive):
                    continue

                # Known installation patterns per drive
                candidates.update([
                    os.path.join(drive, 'ComfyUI', 'models'),
                    os.path.join(drive, 'AI', 'ComfyUI', 'models'),
                    os.path.join(drive, 'StabilityMatrix', 'Packages', 'ComfyUI', 'models'),
                    os.path.join(drive, 'stable-diffusion', 'ComfyUI', 'models'),
                ])

                # Scan first-level directories on each drive for ComfyUI
                try:
                    for entry in os.scandir(drive):
                        if not entry.is_dir():
                            continue
                        name_lower = entry.name.lower()
                        # Skip system/hidden directories
                        if name_lower.startswith(('.', '$')) or name_lower in (
                            'windows', 'program files', 'program files (x86)',
                            'programdata', 'recovery', 'system volume information',
                        ):
                            continue
                        # Direct models folder
                        candidates.add(os.path.join(entry.path, 'models'))
                        # ComfyUI subfolder
                        candidates.add(os.path.join(entry.path, 'ComfyUI', 'models'))
                except (PermissionError, OSError):
                    pass
        else:
            # Linux / macOS / Docker
            home = os.path.expanduser('~')
            candidates.update([
                os.path.join(home, 'ComfyUI', 'models'),
                os.path.join(home, 'AI', 'ComfyUI', 'models'),
                os.path.join(home, 'stable-diffusion', 'ComfyUI', 'models'),
            ])
            # Common Docker / cloud mount points
            candidates.update([
                '/models',
                '/app/models',
                '/comfyui/models',
                '/opt/ComfyUI/models',
                '/workspace/ComfyUI/models',
                '/workspace/models',
            ])

        # Evaluate each candidate
        found_paths = []
        seen = set()

        for path in sorted(candidates):
            abs_path = os.path.abspath(path)
            if abs_path in seen:
                continue
            seen.add(abs_path)

            if not os.path.isdir(abs_path):
                continue

            has_subfolders = False
            model_count = 0

            for subfolder in MODEL_SUBFOLDERS.keys():
                subfolder_path = os.path.join(abs_path, subfolder)
                if os.path.isdir(subfolder_path):
                    has_subfolders = True
                    try:
                        for root, dirs, files in os.walk(subfolder_path):
                            for f in files:
                                if any(f.lower().endswith(ext) for ext in MODEL_EXTENSIONS):
                                    model_count += 1
                    except (PermissionError, OSError):
                        pass

            if has_subfolders:
                found_paths.append({
                    'path': abs_path,
                    'model_count': model_count,
                    'status': 'valid'
                })

        # Sort: most models first
        found_paths.sort(key=lambda p: p['model_count'], reverse=True)

        return jsonify({
            'status': 'success',
            'paths': found_paths
        })
