# Intro to Figure Generation Prompt

## Task

Given a video intro (output from `srt2intro-prompt.md`), generate a 16:9 figure image using the Qwen-Image API (`qwen-image-2.0-pro`).

The image should visually represent the video's core topic — striking, instantly readable, rendered in whatever art direction best fits *this* video (not a fixed house style), with the Chinese video title rendered inside the image (Qwen-Image excels at complex Chinese text rendering).

---

## Input Format

Paste the intro text below (the output from the intro prompt):

```
<INSERT INTRO TEXT HERE>
```

---

## Instructions

1. Read the intro: titles, summary, and chapter list.
2. Identify the single most important visual concept from the content — one scene, not a collage.
3. Compose one **Chinese** text-to-image prompt that:
   - **Opens by naming a deliberate art direction** chosen to fit this specific topic and to look different from recent figures — not a reflexive sci-fi/neon scene. See "Visual style — make every figure look different".
   - Describes one concrete scene: composition, foreground/background, lighting, mood.
   - Is visually bold within the chosen style — a clean focal point that survives small sizes.
   - **Renders the Chinese title inside the image** as large, high-contrast typography. Quote every piece of rendered text with `「」` and state where it appears, for example: 画面上方中央以醒目的白色大字标题写着「……」.
4. Call the DashScope API (below) to generate the image at `2688*1536` (16:9 landscape). Generate exactly one image (`n: 1`).
5. Download the returned image URL immediately (it expires after 24 hours) and save it as `/home/isomoes/Videos/resource/<video-name>.png` by default. Create the resource directory when needed. Use another path only when the user explicitly provides one.

---

## API Call

**Endpoint:** `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`

`DASHSCOPE_API_KEY` must be set in the environment.

```bash
curl --location 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  --header 'Content-Type: application/json' \
  --header "Authorization: Bearer $DASHSCOPE_API_KEY" \
  --data '{
    "model": "qwen-image-2.0-pro",
    "input": {
      "messages": [
        {
          "role": "user",
          "content": [
            { "text": "<YOUR COMPOSED IMAGE PROMPT>" }
          ]
        }
      ]
    },
    "parameters": {
      "n": 1,
      "negative_prompt": " ",
      "prompt_extend": true,
      "watermark": false,
      "size": "2688*1536"
    }
  }'
```

Replace `<YOUR COMPOSED IMAGE PROMPT>` with the prompt composed in step 3.

The response contains the image URL at `output.choices[0].message.content[0].image`. The link is valid for **24 hours only** — download it right away:

```bash
curl -sL -o <video-name>.png "<returned image URL>"
```

**Parameter notes:**

- `size` — `宽*高` format; total pixels must be between 512\*512 and 2048\*2048, rounded to multiples of 16. Always pass `2688*1536` (16:9, YouTube/Bilibili cover ratio) explicitly.
- `prompt_extend` — server-side prompt rewriting, on by default. Pass `false` when exact control over rendered text matters.
- `seed` — optionally fix for more stable regeneration.
- `watermark` — keep `false` (no "Qwen-Image" watermark).

---

## Visual style — make every figure look different

The biggest failure mode is **sameness**: every figure drifting into the same `深蓝色数字空间 + 霓虹蓝紫 + 发光水晶/能量球 + 科幻电影感` look. Treat sci-fi/neon as **one option among many, not the default** — reach for it only when the topic is genuinely about that, and even then find a fresher take. State the chosen style as the **first words** of the prompt (Qwen weights the opening hardest), e.g. `等距 3D 黏土渲染：……` or `复古丝网印刷海报：……`.

Pick or mix from a wide palette — let the topic drive the choice:

| 题材线索 | 可选风格方向 |
| --- | --- |
| 硬件 / 产品 / 评测 | 微距实拍、产品棚光摄影、爆炸图 exploded view |
| 工具 / 工作流 / 效率 | 扁平矢量插画、等距 isometric 微缩场景、信息图 |
| 历史 / 人文 / 文化 | 水墨、工笔、剪纸、浮世绘、国潮、油画 |
| 财经 / 数据 / 商业 | 瑞士国际主义版式、Bauhaus 几何、立体数据图表 |
| 新闻 / 观点 / 人物 | 黑白高反差摄影、杂志封面、电影剧照 |
| 趣味 / 科普 / 故事 | 黏土定格动画、手绘白板、拼贴 collage、像素风 |

This table is a starting palette, not a closed list — combine, subvert, or invent a direction when the topic suggests one.

---

## Prompt template (adapt, don't copy)

A reliable figure prompt follows the order *style → scene → lighting → color → text*. Adapt this skeleton — do **not** paste it verbatim:

```
<风格方向>：<一句话主体场景：主角 + 动作或状态 + 前景/背景>，<光线与氛围>，<高对比度配色>。构图铺满 16:9 宽幅画面，右下角留空。画面上方中央以醒目的大字标题写着「<≤12字标题>」，下方一行小字标签写着「<可选关键词>」。
```

1. **风格方向** — the art direction, first (see the table above).
2. **主体场景** — one concrete subject doing or being something; it should carry an emotion, not just depict the topic.
3. **光线与氛围** — 棚光 / golden hour / 逆光 / 戏剧侧光 — this single detail sets the mood.
4. **配色** — name a high-contrast scheme (深底亮主体 or 亮底深主体); avoid muddy mid-tones.
5. **构图约束** — compose boldly for the full 16:9 frame; keep the lower-right corner clear (YouTube and Bilibili overlay the video duration badge there).
6. **文字** — quote every rendered string with `「」`, put each text block on its own line, and state its position; ask for a font *style* (`简洁无衬线`, `书法体`, `衬线`), never a brand font name.

**Qwen text-rendering notes:** quoting strings raises rendering accuracy sharply; one big title plus at most one short subhead is the safe ceiling — more text means more garbled glyphs; naming a font *style* works, naming a font *brand* does not.

---

## Prompt guidelines

- One powerful visual + a short bold title — that is the whole figure.
- Keep rendered text short and few: one main title (ideally ≤ 12 个汉字 — abbreviate the intro's 中文标题 if needed), plus at most 1-2 short keyword labels.
- Large high-contrast title, simple composition, no dense detail that disappears at small sizes.
- Keep technical identifiers and product names (for example Claude Code, MCP, API) in their original language.
- Stay well under the 1300-token prompt limit of the qwen-image-2.0 series; anything longer is truncated automatically.
- Do not put watermark, logo, or border instructions in the prompt; the API call already disables the watermark.
- Good (科幻，仅当题材真正契合): `深蓝色数字隧道中，三枚发光的能量球并排疾驰，速度线与霓虹光效，电影感，高对比度。画面中央以醒目的白色大字标题写着「Agent 实测对比」`
- Good (扁平插画): `扁平矢量插画，明黄底色，中央一枚被放大镜照亮的红色邮票图标，简洁几何阴影。画面上方以黑色无衬线大字标题写着「邮件协议简史」，左右两侧留白`
- Good (等距 3D): `等距 3D 微缩渲染：木质书桌上一台打开的笔记本电脑，桌面漂浮着齿轮与文档图标，柔和棚光，奶油色背景。画面顶部以深蓝大字标题写着「自动化工作流」`
- Avoid: vague prompts like 「一张与 AI 相关的图片」
- Avoid: rendering the full long title or whole sentences — abbreviate to a punchy phrase.
- Avoid: defaulting to the `深蓝数字空间 / 霓虹 / 发光水晶` sci-fi look out of habit.

---

## Output

- The generated image file saved as `/home/isomoes/Videos/resource/<video-name>.png` by default.
- No additional text output required.

---

## Example

Given intro for `agent-bench.txt`:

```
中文标题：Claude Code 实测对比
English Title: Claude Code Agent Benchmark

This video benchmarks multiple LLMs inside real agent workflows...

00:00  back
01:03  intro
...
```

Composed image prompt:

```
电影感科幻场景：深蓝色数字隧道中，多枚发光的能量球并排疾驰，速度线与霓虹光效，高对比度。构图铺满 16:9 宽幅画面，右下角留空。画面中央以醒目的白色大字标题写着「Claude Code 实测对比」，下方一行小字标签写着「Agent Benchmark」
```

API call with `"model": "qwen-image-2.0-pro"` and `"size": "2688*1536"`; download the returned URL and save as `/home/isomoes/Videos/resource/agent-bench.png`.
