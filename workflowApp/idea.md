Objectif du projet : Créer une application desktop self-contained appelée "Local AI Workflows" (ou nom à définir), qui permet de construire et exécuter des workflows visuels entre plusieurs modèles IA locaux (via Ollama), sans aucune connexion internet après l'installation initiale.

Caractéristiques principales :
- Fonctionne entièrement en local sur Windows 11 (RTX 4060, 32 Go RAM)
- Interface desktop native (pas un site web dans le navigateur)
- Stack technique : Tauri (Rust backend léger) + Vue 3 (Composition API, <script setup>) + Vite + Vue Flow (pour le canvas node-based)
- Style moderne, dark mode par défaut, look pro et intuitif (inspiré n8n / Flowise mais plus poli)

Structure de l’interface (tabs principaux) :
1. Tab "Workflow Builder" : canvas node-based avec Vue Flow
   - Nodes personnalisables : drag & drop, zoom/pan, minimap, controls
   - Types de nodes de base prévus :
     - User Input (textarea pour instruction initiale)
     - LLM Call (choix du modèle Ollama, prompt template, température, etc.)
     - Condition / Switch (branchement if/else sur output)
     - File Read / Write (gestion fichiers projet)
     - Shell Execute (lancer commandes comme npm run dev, pytest, etc.)
     - Human Review (pause + popup édition/validation)
     - Output / Display (affiche texte, code, logs)
     - Memory / Context Saver (persistance variables entre nodes)
   - Possibilité d’enchaîner les nodes pour créer des flux complexes (ex. User → R1 Plan → Validation → Coder Code → Tests → Itération si erreur)

2. Tab "Chat simple" : mode rapide pour discuter directement avec un modèle Ollama (fallback one-shot ou test rapide)

3. Tab "Code Editor" : éditeur lightweight intégré
   - Arbre de fichiers projet
   - Monaco Editor ou CodeMirror
   - Preview diff quand un node Coder propose des changements
   - Terminal intégré en bas pour voir les sorties de commandes lancées par les nodes

4. Autres tabs futurs : History & Debug, Models Hub (gestion Ollama locale), Agents préconfigurés

Rôles IA principaux (à spécialiser via des nodes LLM Call distincts) :
- R1 / Planificateur : modèle fort en raisonnement structuré et décomposition de tâches (ex. GLM-4.7, Kimi-K2, DeepSeek-V3 thinking, Ministral 14B, etc. ~14-32B quantizé)
- Coder : modèle spécialisé génération de code propre et précis (ex. Qwen3-Coder 14B/32B, MiniMax-M2.1, Devstral-2, GLM-4.7 aussi)

Objectifs globaux du projet :
- Confidentialité totale : rien ne sort de la machine
- Zéro coût récurrent après installation
- Indépendance vis-à-vis des Big Tech / APIs cloud
- Plaisir de tout faire tourner localement + apprentissage agents / prompting / workflows
- Extensible au-delà du dev : rédaction, analyse, automation perso, etc.

Contraintes techniques :
- Tout via Ollama (localhost:11434)
- Pas d'installation de packages externes pendant l'exécution (seulement au build Tauri)
- Performances adaptées à RTX 4060 (modèles jusqu'à ~34B Q5/Q6 en inférence acceptable)

Maintenant, aide-moi à avancer sur ce projet de manière concrète et pas à pas.
