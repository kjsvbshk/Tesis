import os

file_path = "app/services/snapshot_service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Change 1: First SELECT mapping
old1 = '''                        SELECT external_event_id, resolution_confidence
                        FROM espn.odds_event_game_map
                        WHERE game_id = :game_id
                        ORDER BY last_verified_at DESC NULLS LAST, created_at DESC
                        LIMIT 1'''
new1 = '''                        SELECT odds_id
                        FROM espn.odds_event_game_map
                        WHERE game_id = :game_id
                        LIMIT 1'''
content = content.replace(old1, new1)

# Change 2: Handle mapping result
old2 = '''                external_event_id = None
                if mapping_result:
                    external_event_id = mapping_result[0]
                    resolution_confidence = mapping_result[1] if len(mapping_result) > 1 else None
                    print(f"✅ Mapeo encontrado: game_id={game_id} → external_event_id={external_event_id} (confianza: {resolution_confidence})")'''
new2 = '''                external_event_id = None
                if mapping_result:
                    external_event_id = mapping_result[0]
                    print(f"✅ Mapeo encontrado: game_id={game_id} → odds_id={external_event_id}")'''
content = content.replace(old2, new2)

# Change 3: Second SELECT mapping
old3 = '''                                                    SELECT id, game_id, resolution_confidence, needs_review
                                                    FROM espn.odds_event_game_map
                                                    WHERE external_event_id = :external_event_id
                                                """),
                                                {"external_event_id": external_event_id_from_odds}'''
new3 = '''                                                    SELECT game_id
                                                    FROM espn.odds_event_game_map
                                                    WHERE odds_id = :odds_id
                                                """),
                                                {"odds_id": external_event_id_from_odds}'''
content = content.replace(old3, new3)

# Change 4: Handle second mapping result
old4 = '''                                                # Mapping existe: NO actualizar automáticamente (política FASE 4.1)
                                                existing_game_id = existing_mapping[1]
                                                if existing_game_id != game_id:
                                                    print(f"⚠️  Mapping existente con game_id diferente: {existing_game_id} vs {game_id}. NO se actualiza automáticamente.")
                                                else:
                                                    print(f"ℹ️  Mapping ya existe: external_event_id={external_event_id_from_odds} → game_id={game_id}")'''
new4 = '''                                                # Mapping existe: NO actualizar automáticamente (política FASE 4.1)
                                                existing_game_id = existing_mapping[0]
                                                if existing_game_id != game_id:
                                                    print(f"⚠️  Mapping existente con game_id diferente: {existing_game_id} vs {game_id}. NO se actualiza automáticamente.")
                                                else:
                                                    print(f"ℹ️  Mapping ya existe: odds_id={external_event_id_from_odds} → game_id={game_id}")'''
content = content.replace(old4, new4)

# Change 5: INSERT mapping
old5 = '''                                                        INSERT INTO espn.odds_event_game_map 
                                                        (external_event_id, game_id, resolved_by, resolution_method, resolution_confidence, resolution_metadata)
                                                        VALUES (:external_event_id, :game_id, :resolved_by, :resolution_method, :confidence, :metadata)
                                                    """),
                                                    {
                                                        "external_event_id": external_event_id_from_odds,
                                                        "game_id": game_id,
                                                        "resolved_by": "date_teams" if has_teams else "date",
                                                        "resolution_method": resolution_method,
                                                        "confidence": resolution_confidence,
                                                        "metadata": f'{{"game_date": "{game_date}", "home_team": "{game_home_team}", "away_team": "{game_away_team}"}}'
                                                    }'''
new5 = '''                                                        INSERT INTO espn.odds_event_game_map 
                                                        (odds_id, game_id)
                                                        VALUES (:odds_id, :game_id)
                                                    """),
                                                    {
                                                        "odds_id": external_event_id_from_odds,
                                                        "game_id": game_id
                                                    }'''
content = content.replace(old5, new5)

# Change 6: the print after INSERT
old6 = '''print(f"✅ Mapeo creado: external_event_id={external_event_id_from_odds} → game_id={game_id} (método: {resolution_method}, confianza: {resolution_confidence})")'''
new6 = '''print(f"✅ Mapeo creado: odds_id={external_event_id_from_odds} → game_id={game_id}")'''
content = content.replace(old6, new6)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("done")
