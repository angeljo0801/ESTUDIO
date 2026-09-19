from pathlib import Path
import subprocess

p = Path('v159_agent_orchestrator_directory_patch.py')
s = p.read_text()

replacements = [
    ("profiles = r'''", 'profiles = r"""'),
    ("\n'''\n\nagent_page = r'''", '\n"""\n\nagent_page = r"""'),
    ("\n'''\n\norchestrator = r'''", '\n"""\n\norchestrator = r"""'),
    ("\n'''\n\nPath('lib/agent_profiles.dart')", '\n"""\n\nPath(\'lib/agent_profiles.dart\')'),
]
for old, new in replacements:
    if old not in s:
        raise SystemExit('v161 source delimiter anchor missing: ' + old[:40])
    s = s.replace(old, new, 1)
p.write_text(s)

subprocess.run(['python3', 'v159_agent_orchestrator_directory_patch.py'], check=True)
subprocess.run(['python3', 'v160_agent_orchestrator_compile_fix.py'], check=True)
subprocess.run(['python3', 'v162_unified_prompt_generators_patch.py'], check=True)
subprocess.run(['python3', 'v163_orchestrator_bottom_safe_area_patch.py'], check=True)
subprocess.run(['python3', 'v164_orchestrator_agent_descriptions_patch.py'], check=True)
subprocess.run(['python3', 'v165_general_ai_translate_timer_patch.py'], check=True)
subprocess.run(['python3', 'v166_chat_copy_selection_patch.py'], check=True)
subprocess.run(['python3', 'v167_vector_embeddings_patch.py'], check=True)
subprocess.run(['python3', 'v168_vector_learning_features_patch.py'], check=True)
subprocess.run(['python3', 'v169_manual_cards_copy_row_patch.py'], check=True)
subprocess.run(['python3', 'v170_per_dashboard_ai_settings_patch.py'], check=True)
subprocess.run(['python3', 'v171_indexed_card_generation_patch.py'], check=True)
subprocess.run(['python3', 'v172_restore_original_manual_cards_patch.py'], check=True)
subprocess.run(['python3', 'v173_smart_pdf_extractor_patch.py'], check=True)
subprocess.run(['python3', 'v174_pdf_provenance_data_patch.py'], check=True)
subprocess.run(['python3', 'v175_card_quality_source_ui_patch.py'], check=True)
subprocess.run(['python3', 'v176_ai_card_final_review_target_patch.py'], check=True)
subprocess.run(['python3', 'v177_library_ai_settings_patch.py'], check=True)
subprocess.run(['python3', 'v179_mandatory_progressive_ai_card_review_patch.py'], check=True)
subprocess.run(['python3', 'v180_slow_ai_review_resilience_patch.py'], check=True)
subprocess.run(['python3', 'v181_card_review_foreground_service_patch.py'], check=True)
subprocess.run(['python3', 'v183_final_card_pipeline_patch.py'], check=True)
print('v161 applied: v159 source repaired; directory generated; v160-v183 fixes applied')
