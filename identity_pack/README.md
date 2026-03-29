# Identity Metadata — Referencia técnica

Documentación de `identity_metadata.json`: qué hace cada campo, qué método lo consume y qué ajustar para cambiar el comportamiento.

> `days_elapsed` se incrementa 1 por cada post generado (no por día calendario).

---

## Estructura general

```
identity_metadata.json
├── meta                  # Versión y notas (no se usa en runtime)
├── assets                # Rutas a imágenes de referencia
├── caption               # Todo lo que afecta la generación de texto
├── narrative             # Arco narrativo: capítulos, emociones, ubicaciones
└── image                 # Todo lo que afecta la generación de imágenes
```

---

## 1. `assets`

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `reference_images` | Lista de imágenes de referencia para consistencia facial | `image_gen.get_reference_images()` |
| `base_images` | Imágenes originales (no se borran en rotación) | `state_engine._update_identity_pack_if_needed()` |
| `generated_images` | Imágenes generadas que se agregaron al pack | `state_engine._update_identity_pack_if_needed()` |

**Ajuste típico:** agregar/quitar fotos de referencia para cambiar la identidad visual base.

---

## 2. `caption`

### 2.1 Identidad y voz

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `influencer_name` | Nombre que aparece en el prompt de caption | `text_gen.generate_caption()` → prompt de usuario |
| `description` | Descripción de la personalidad | `text_gen.generate_caption()` → prompt de usuario |
| `voice_tone` | Tono de voz (reflexivo, irónico, etc.) | `text_gen.generate_caption()` → prompt de usuario |
| `style_notes` | Notas de estilo visual/atmosférico | `text_gen.generate_caption()` → prompt de usuario |
| `themes` | Temas macro de la cuenta | No se usa en runtime actualmente |
| `palette.primary` | Colores primarios de la paleta emocional | `text_gen.generate_caption()` → "Referencias estéticas" |
| `palette.mood` | Mood de la paleta | `text_gen.generate_caption()` → "Paleta emocional" |

### 2.2 Persona y humor

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `persona.name` | Nombre interno del personaje | No se usa en runtime |
| `persona.self_definition` | Autodefinición | No se usa en runtime |
| `persona.personality.humor_profile.modes` | Modos de humor disponibles | No se usa en runtime (potencial para futuro) |
| `persona.personality.humor_profile.guardrails` | Límites del humor | No se usa en runtime |

### 2.3 Guidelines de caption

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `guidelines.length` | Rango de palabras | No se usa directamente (hardcoded en prompt como 50-80) |
| `guidelines.style` | Estilos de escritura | No se usa en runtime |
| `guidelines.must_include` | Requisitos obligatorios | No se usa directamente (hardcoded en prompt) |
| `guidelines.forbidden` | Elementos prohibidos | No se usa directamente (hardcoded en prompt) |
| `guidelines.devices` | Recursos literarios | No se usa en runtime |
| `guidelines.emoji_policy` | Política de emojis | No se usa directamente (hardcoded en prompt) |

**Nota:** Los campos de `guidelines` están duplicados como texto literal en el prompt de `generate_caption()`. Para que cambios en el JSON tengan efecto, habría que refactorizar el prompt para leerlos dinámicamente.

### 2.4 Tone variations

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `tone_variations` | Pool de 8 tonos narrativos; se elige 1 al azar por post | `text_gen.generate_caption()` → system prompt + instrucciones |

**Ajuste típico:** agregar tonos nuevos para más variedad en la voz narrativa. Cada post elige uno al azar.

### 2.5 Prompt sanitizer

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `prompt_sanitizer.ban_phrases` | Frases prohibidas que se eliminan post-generación | `text_gen.generate_caption()` y `image_gen.build_visual_prompt()` |
| `prompt_sanitizer.replace_map` | Reemplazos de frases grandilocuentes | `text_gen.generate_caption()` y `image_gen.build_visual_prompt()` |
| `prompt_sanitizer.append_safe_suffix` | Sufijo que se agrega al prompt visual | `image_gen.build_visual_prompt()` |

**Ajuste típico:** agregar frases a `ban_phrases` si el modelo insiste en usar expresiones no deseadas.

---

## 3. `narrative`

### 3.1 Chapter windows

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `chapter_windows[].name` | Nombre del capítulo narrativo | `state_engine._evolve_chapter_by_days()` |
| `chapter_windows[].min_days` | Post mínimo para entrar al capítulo | `state_engine._evolve_chapter_by_days()` |
| `chapter_windows[].max_days` | Post máximo (null = sin límite) | `state_engine._evolve_chapter_by_days()` |

Capítulos actuales: `despertar` (0-59) → `búsqueda` (60-119) → `encuentro` (120-179) → `integración` (180+).

**Ajuste típico:** cambiar rangos para acelerar o ralentizar la progresión narrativa.

### 3.2 Learning goals

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `learning_goals.{chapter}` | Meta de aprendizaje por capítulo | `state_engine._evolve_learning_goal()` → se incluye en caption |

Fijo por capítulo. Cambia solo cuando cambia el capítulo.

### 3.3 Emotion cycle

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `emotion_cycle` | Pool de 9 emociones disponibles | `state_engine._evolve_emotion()` |

**Mecanismo:** selección aleatoria ponderada. La emoción actual recibe peso 0.05 (casi nunca se repite), emociones recientes (últimas 5) reciben peso 0.3, el resto peso 1.0. Las emociones recientes se guardan en `state.meta.recent_emotions`.

**Ajuste típico:** agregar emociones nuevas al pool para ampliar el rango emocional.

### 3.4 Location arcs

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `location_arcs[].name` | Nombre descriptivo del arco | Solo logging |
| `location_arcs[].min_days` | Post mínimo para entrar al arco | `state_engine._evolve_location_by_arc()` |
| `location_arcs[].max_days` | Post máximo (null = sin límite) | `state_engine._evolve_location_by_arc()` |
| `location_arcs[].locations` | Ubicaciones del arco (se rotan secuencialmente) | `state_engine._evolve_location_by_arc()` |

**Mecanismo:** rotación secuencial dentro del arco. Cada post avanza a la siguiente ubicación de la lista. Cuando llega al final, vuelve al inicio del mismo arco. Arcos actuales: 5-7 posts cada uno, viaje completo ~71 posts.

**Ajuste típico:** agregar ubicaciones a un arco existente, crear arcos nuevos, cambiar rangos para quedarse más o menos tiempo en una zona.

---

## 4. `image`

### 4.1 Controles globales

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `identity_strength` | Peso de referencia facial (0-1) | `image_gen.generate_image()` → `ip_adapter_scale` |
| `style_strength` | Peso de estilo (0-1) | `image_gen.generate_image()` → `controlnet_conditioning_scale` |

### 4.2 Prompt guidelines

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `prompt_guidelines.expression_pool` | Pool de 15 expresiones faciales; se eligen 2 al azar por imagen | `image_gen.build_visual_prompt()` → boosts |
| `prompt_guidelines.wardrobe_defaults` | Reglas de vestuario fijas (modestia, etc.) | `image_gen.build_visual_prompt()` → boosts (siempre incluidas) |
| `prompt_guidelines.base_quality_tags` | Tags de calidad base del prompt | `image_gen.build_visual_prompt()` → base_prompt |
| `prompt_guidelines.anti_grey_tags` | Tags anti-gris que se agregan al final | `image_gen.build_visual_prompt()` |
| `prompt_guidelines.scene_type_cues` | Cue textual por tipo de escena (urban, rural, etc.) | `image_gen._scene_cue()` |
| `prompt_guidelines.location_cues` | Cue textual simple por ciudad (fallback) | `image_gen._extract_location_cue()` |
| `prompt_guidelines.location_fallback` | Cue por defecto si no hay match | `image_gen._extract_location_cue()` |
| `prompt_guidelines.location_render_policy` | Controla cuántos detalles de location se inyectan | `image_gen._extract_location_cue()` y `text_gen.generate_caption()` |

### 4.3 Location profiles

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `prompt_guidelines.location_profiles.{city}` | Perfil visual detallado por ciudad | `image_gen._extract_location_cue()` y `text_gen._build_location_anchor()` |
| `.aliases` | Nombres alternativos para matching | Match en `_match_location_profile()` |
| `.visual_signatures` | Elementos visuales del lugar | Se muestrean aleatoriamente (max 3) |
| `.landmarks` | Landmarks reconocibles | Se muestrean (max 1) |
| `.street_furniture` | Mobiliario urbano/rural | Se muestrean (max 1) |
| `.sensory_tokens` | Tokens sensoriales (olor, sonido, tacto) | Se usan en captions via `_build_location_anchor()` |
| `.climate_light` | Descripción de la luz del lugar | Se agrega siempre al prompt visual |

**Ajuste típico:** agregar perfiles para ciudades nuevas. Asegurarse de que cada ciudad en `location_arcs` tenga un perfil o al menos un `location_cue`.

### 4.4 Generation defaults

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `generation_defaults.engine` | Motor de generación | Solo referencia |
| `generation_defaults.framing_tags` | Vacío — antes inyectaba framing estático | `image_gen.build_visual_prompt()` (ignorado si vacío) |
| `generation_defaults.lighting_tags` | Vacío — antes inyectaba lighting estático | `image_gen.build_visual_prompt()` (ignorado si vacío) |
| `generation_defaults.model_input_defaults` | Defaults para Stable Diffusion / IP-Adapter | `image_gen.generate_image()` (rama no-NanoBanana) |

**Nota:** `framing_tags` y `lighting_tags` están vacíos intencionalmente. El framing viene de `composition_policy.shot_prompt_map` y el lighting de `appearance_variation.camera_lighting`. Llenarlos agregaría bias estático.

### 4.5 Photorealism y NSFW

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `photorealism.keywords` | Tags de fotorrealismo (siempre se incluyen) | `image_gen.build_visual_prompt()` → primer boost |
| `nsfw_filters.negative_prompt` | Prompt negativo enviado al modelo | `image_gen.generate_image()` → Nano Banana y otros modelos |
| `nsfw_filters.safety_hints` | Hints de seguridad (no se usan en prompt directo) | Referencia |

### 4.6 Mood controls

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `mood_controls.cheerful_boost` | Tags de ánimo para emociones positivas | `image_gen.build_visual_prompt()` → `mood:` en base_prompt |
| `mood_controls.neutral_dial` | Tags de ánimo para emociones neutras/negativas | `image_gen.build_visual_prompt()` → `mood:` en base_prompt |
| `mood_controls.positive_emotions` | Lista de emociones consideradas "positivas" | `image_gen.build_visual_prompt()` → decide cheerful vs neutral |

### 4.7 Composition policy

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `composition_policy.no_repeat_window` | Ventana anti-repetición (4 posts) | `image_gen.select_visual_decision()` |
| `composition_policy.shot_weights` | Pesos de 6 tipos de encuadre | `image_gen.select_visual_decision()` → `random.choices` |
| `composition_policy.pose_weights` | Pesos de 10 poses | `image_gen.select_visual_decision()` → `random.choices` |
| `composition_policy.scene_weights` | Pesos de 5 tipos de escena | `image_gen.select_visual_decision()` → `random.choices` |
| `composition_policy.shot_prompt_map` | Texto descriptivo por tipo de shot | `image_gen.select_visual_decision()` → `shot_prompt` |
| `composition_policy.pose_prompt_map` | Texto descriptivo por pose | `image_gen.select_visual_decision()` → `pose_prompt` |
| `composition_policy.emotion_overrides` | Ajustes de pesos por emoción | `image_gen.select_visual_decision()` → merge sobre base |
| `composition_policy.chapter_overrides` | Ajustes de pesos por capítulo | `image_gen.select_visual_decision()` → merge sobre base |

**Mecanismo:** `select_visual_decision()` toma los pesos base, aplica overrides de emoción y capítulo, luego penaliza opciones repetidas en la ventana reciente (shots ×0.3, poses ×0.4), y elige con `random.choices`.

**Ajuste típico:**
- Agregar más poses: agregar key en `pose_weights` + texto en `pose_prompt_map`
- Cambiar distribución: ajustar pesos (deben sumar ~1.0 pero se normalizan)
- Agregar overrides por emoción: agregar objeto en `emotion_overrides.{emocion}`

### 4.8 Appearance variation

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `appearance_variation.hair_presets` | Pool de 8 peinados | `image_gen._sample_look()` → `hair` |
| `appearance_variation.palettes` | 4 paletas con colores | `image_gen._sample_look()` → `palette` |
| `appearance_variation.outfit_archetypes` | Pool de 6 estilos de outfit | `image_gen._sample_look()` → `archetype` |
| `appearance_variation.textures` | Pool de 5 texturas de tela | `image_gen._sample_look()` → `texture` |
| `appearance_variation.accessories` | Pool de 5 accesorios | `image_gen._sample_look()` → `accessory` |
| `appearance_variation.camera_lighting.angles` | Pool de 3 ángulos de cámara | `image_gen._sample_look()` → `angle` |
| `appearance_variation.camera_lighting.lighting` | Pool de 3 tipos de iluminación | `image_gen._sample_look()` → `lighting` |
| `appearance_variation.avoid` | Elementos a evitar | `image_gen._sample_look()` → `avoid` |

**Mecanismo:** `_sample_look()` elige 1 de cada pool al azar, evitando valores usados en los últimos 7 posts (configurado en `look_rotation.no_repeat_window`). Los looks recientes se guardan en `state.meta.look`.

**Ajuste típico:** agregar más opciones a cualquier pool para más variedad. Más opciones = menos repeticiones.

### 4.9 Look rotation

| Campo | Qué hace | Consumido por |
|-------|----------|---------------|
| `look_rotation.no_repeat_window` | Cuántos posts recordar para evitar repetir looks | `image_gen._sample_look()` |
| `look_rotation.logic` | Descripción de la lógica (solo documentación) | No se usa en runtime |

---

## Pipeline de generación — flujo completo

```
1. state_engine.next_state()
   ├── _evolve_chapter_by_days()     ← narrative.chapter_windows
   ├── _evolve_emotion()             ← narrative.emotion_cycle + meta.recent_emotions
   ├── _evolve_location_by_arc()     ← narrative.location_arcs
   └── _evolve_learning_goal()       ← narrative.learning_goals

2. image_gen.select_visual_decision()
   ├── composition_policy.shot_weights      → tipo de encuadre
   ├── composition_policy.pose_weights      → pose
   ├── composition_policy.scene_weights     → tipo de escena
   ├── composition_policy.emotion_overrides → ajustes por emoción
   ├── composition_policy.chapter_overrides → ajustes por capítulo
   └── meta.recent_visual_decisions         → anti-repetición

3. text_gen.generate_caption()
   ├── caption.influencer_name, description, voice_tone
   ├── caption.palette.mood
   ├── caption.tone_variations              → tono aleatorio por post
   ├── caption.prompt_sanitizer             → limpieza post-generación
   ├── narrative state (chapter, emotion, location, learning_goal)
   └── location_profiles → _build_location_anchor() → ancla sensorial

4. image_gen.build_visual_prompt()
   ├── _sample_look()                       ← appearance_variation + look_rotation
   │   ├── hair_presets
   │   ├── palettes
   │   ├── outfit_archetypes
   │   ├── textures, accessories
   │   └── camera_lighting (angles, lighting)
   ├── expression_pool                      → 2 expresiones aleatorias
   ├── wardrobe_defaults                    → restricciones fijas
   ├── photorealism.keywords                → calidad
   ├── mood_controls                        → mood tags según emoción
   ├── _extract_location_cue()              ← location_profiles / location_cues
   ├── select_visual_decision result        → framing, pose, scene
   └── nsfw_filters.negative_prompt         → enviado a Nano Banana

5. image_gen.generate_image()
   ├── build_visual_prompt() output → prompt
   ├── reference_images             → image_input
   └── nsfw_filters.negative_prompt → negative_prompt
```

---

## Campos NO usados en runtime

Estos campos existen en el JSON pero no se leen en ningún método. Se pueden usar en el futuro o eliminar:

| Campo | Ubicación |
|-------|-----------|
| `caption.themes` | `caption` |
| `caption.persona.name` | `caption.persona` |
| `caption.persona.self_definition` | `caption.persona` |
| `caption.persona.personality.humor_profile` | `caption.persona.personality` |
| `caption.guidelines.*` (length, style, must_include, forbidden, devices, emoji_policy) | `caption.guidelines` |
| `image.nsfw_filters.safety_hints` | `image.nsfw_filters` |
| `image.photorealism.weight` | `image.photorealism` |
| `image.look_rotation.logic` | `image.look_rotation` |

---

## Guía rápida de ajustes

| Quiero... | Cambiar... |
|-----------|------------|
| Más variedad de poses | Agregar entries a `composition_policy.pose_weights` + `pose_prompt_map` |
| Más variedad de encuadres | Agregar entries a `composition_policy.shot_weights` + `shot_prompt_map` |
| Más variedad de outfits | Agregar opciones a `appearance_variation.outfit_archetypes` |
| Más variedad de peinados | Agregar opciones a `appearance_variation.hair_presets` |
| Más variedad de iluminación | Agregar opciones a `appearance_variation.camera_lighting.lighting` |
| Más variedad de expresiones | Agregar opciones a `prompt_guidelines.expression_pool` |
| Más variedad en el tono del texto | Agregar opciones a `caption.tone_variations` |
| Cambiar más rápido de ciudad | Reducir `max_days - min_days` en `narrative.location_arcs` |
| Agregar una ciudad nueva | Agregar a `location_arcs` + crear entry en `location_profiles` + agregar `location_cues` |
| Que una emoción favorezca cierta pose | Agregar override en `composition_policy.emotion_overrides` |
| Evitar que el modelo genere algo | Agregar a `nsfw_filters.negative_prompt` |
| Evitar una frase en captions | Agregar a `caption.prompt_sanitizer.ban_phrases` |
| Menos repeticiones de look | Aumentar `image.look_rotation.no_repeat_window` |
| Menos repeticiones de shot/pose | Aumentar `composition_policy.no_repeat_window` |
