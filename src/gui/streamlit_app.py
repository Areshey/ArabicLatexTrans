import io
import re
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import streamlit as streamlit_backend
import toml

from src.runtime import run_translation, split_multivalue_text
from src.utils.progress import get_progress_backend, set_progress_backend


def _collect_result_pdfs(result: Dict[str, Any]) -> List[str]:
    output_dir = Path(result["output_dir"])
    #target_language = result["config"].get("target_language", "ch") #Set default target language to Arabic ("ar") instead of Chinese ("ch") (updated by Ali)
    target_language = result["config"].get("target_language", "ar") 
    selected: List[str] = []

    for project_dir in result["projects"]:
        project_name = Path(project_dir).name
        project_output_dir = output_dir / f"{target_language}_{project_name}"
        translated_pdf = project_output_dir / f"{target_language}_{project_name}.pdf"
        original_pdf = project_output_dir / project_name / f"{project_name}.pdf"

        if translated_pdf.exists():
            selected.append(str(translated_pdf))
        if original_pdf.exists():
            selected.append(str(original_pdf))

    return selected


class StreamlitLogWriter(io.TextIOBase):
    def __init__(self, placeholder, state: Dict[str, Any]):
        self.placeholder = placeholder
        self.state = state

    def write(self, data: str) -> int:
        if not data:
            return 0

        self.state["raw_buffer"] += data
        normalized = self.state["raw_buffer"].replace("\r", "\n")
        lines = normalized.split("\n")
        self.state["raw_buffer"] = lines.pop() if normalized and not normalized.endswith("\n") else ""

        for line in lines:
            text = line.strip()
            if not text:
                continue
            self.state["logs"].append(text)
            self._update_state_from_line(text)

        self.placeholder.code("\n".join(self.state["logs"][-300:]), language="text")
        return len(data)

    def flush(self) -> None:
        return None

    def _update_state_from_line(self, line: str) -> None:
        project_match = re.search(r"\[(\d+)/(\d+)\]\s+Processing\s+(.+)", line)
        if project_match:
            current = int(project_match.group(1))
            total = int(project_match.group(2))
            name = project_match.group(3).strip()
            #self.state["project_text"].markdown(f"**Project** `{current}/{total}`  `{name}`")
            # Localized the project status message to Arabic(Updated by Imaan Alkhanen)
            self.state["project_text"].markdown(f"**المشروع** `{current}/{total}`  `{name}`"
)
            if total > 0:
                self.state["overall_bar"].progress((current - 1) / total)
            return

        progress_match = re.search(r"(\d+(?:\.\d+)?)%", line)
        if progress_match:
            percent = min(100.0, max(0.0, float(progress_match.group(1))))
            self.state["stage_bar"].progress(percent / 100.0)
            #self.state["stage_text"].markdown(f"**Stage** {line}")
            # Localized the stage status message to Arabic(Updated by Imaan Alkhanen)
            self.state["stage_text"].markdown(f"**المرحلة** {line}")
            return

        if line.startswith("[") or "Error processing project" in line or "Successfully" in line:
            #self.state["stage_text"].markdown(f"**Stage** {line}")
            # Localized the stage status message to Arabic(Updated by Imaan Alkhanen)
            self.state["stage_text"].markdown(f"**المرحلة** {line}")


def _load_defaults(config_path: str) -> Dict[str, Any]:
    try:
        return toml.load(config_path)
    except Exception:
        return {}


def _ensure_session_state() -> None:
    streamlit_backend.session_state.setdefault("job_history", [])
    streamlit_backend.session_state.setdefault("retry_failed_only", False)
    streamlit_backend.session_state.setdefault("retry_payload", None)


def _inject_style() -> None:
    streamlit_backend.set_page_config(
        #page_title="LaTeXTrans Studio",
        # Set the page title to Arabic (Updated by Imaan Alkhanen)
        page_title="منصة ترجمة Latex",
        page_icon="L",
        layout="wide",
    )
    streamlit_backend.markdown(
        # Applied Arabic RTL layout and right-aligned text styling for the user interface(Updated by Imaan Alkhanen)
        """
        <style>
        /* RTL */
        html, body, .stApp {
            direction: rtl;
        }

        h1, h2, h3, h4, h5, h6,
        p, label, span, div {
            text-align: right !important;
        }

        textarea {
            direction: rtl;
            text-align: right;
        }

        .hero-title,
        .hero-subtitle {
            text-align: right !important;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(245, 173, 92, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(26, 96, 107, 0.18), transparent 24%),
                linear-gradient(180deg, #f7f2ea 0%, #f1ede4 100%);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .app-shell {
            padding: 1.25rem 1.5rem;
            border-radius: 24px;
            background: rgba(255, 252, 247, 0.84);
            border: 1px solid rgba(46, 56, 64, 0.08);
            box-shadow: 0 18px 60px rgba(67, 51, 32, 0.10);
            backdrop-filter: blur(12px);
        }
        .hero-title {
            font-size: 2.2rem;
            font-weight: 700;
            line-height: 1.05;
            color: #17323b;
            margin-bottom: 0.35rem;
        }
        .hero-subtitle {
            color: #5f5c53;
            font-size: 1rem;
            margin-bottom: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_form(defaults: Dict[str, Any]) -> Dict[str, Any]:
    llm_defaults = defaults.get("llm_config", {})
    streamlit_backend.sidebar.header("Run Configuration")
    config_path = streamlit_backend.sidebar.text_input("Config Path", "config/default.toml")
    source_language = streamlit_backend.sidebar.text_input("Source Language", defaults.get("source_language", "en"))
    #target_language = streamlit_backend.sidebar.text_input("Target Language", defaults.get("target_language", "ch")) Set default target language to Arabic ("ar")  (updated by Ali)
    target_language = streamlit_backend.sidebar.text_input("Target Language", defaults.get("target_language", "ar"))
    model = streamlit_backend.sidebar.text_input("Model", llm_defaults.get("model", ""))
    base_url = streamlit_backend.sidebar.text_input("Base URL", llm_defaults.get("base_url", ""))
    api_key = streamlit_backend.sidebar.text_input("API Key", llm_defaults.get("api_key", ""), type="password")
    tex_source_dir = streamlit_backend.sidebar.text_input("TeX Source Dir", defaults.get("tex_sources_dir", "tex source"))
    output_dir = streamlit_backend.sidebar.text_input("Output Dir", defaults.get("output_dir", "outputs"))
    mode_options = {"0 - Normal": 0, "1 - Retry Errors": 1, "2 - Alt": 2}
    selected_mode = streamlit_backend.sidebar.selectbox("Mode", list(mode_options.keys()), index=0)
    update_term = streamlit_backend.sidebar.checkbox(
        "Update Terms",
        value=str(defaults.get("update_term", "False")) == "True",
    )
    all_existing = streamlit_backend.sidebar.checkbox("Process All Existing Projects", value=False)
    user_term = streamlit_backend.sidebar.text_area(
        "User Terms",
        defaults.get("user_term", ""),
        height=120,
        help="Optional terminology guidance passed through the existing config field.",
    )

    return {
        "config_path": config_path,
        "source_language": source_language.strip() or "en",
        #"target_language": target_language.strip() or "ch", Set default target language to Arabic ("ar")  (updated by Ali)
        "target_language": target_language.strip() or "ar",
        "model": model.strip(),
        "url": base_url.strip(),
        "key": api_key.strip(),
        "source": tex_source_dir.strip(),
        "output": output_dir.strip(),
        "mode": mode_options[selected_mode],
        "update_term": "True" if update_term else "False",
        "all_existing": all_existing,
        "user_term": user_term.strip(),
    }

## Updated UI labels, placeholders, and help text to Arabic (Updated by Imaan Alkhanen)
def _collect_inputs() -> Dict[str, List[str]]:
    left, right = streamlit_backend.columns([1.15, 0.85], gap="large")
    with left:
        #arxiv_text = streamlit_backend.text_area(
         #   "arXiv IDs",
        #    value="",
         #   height=120,
         #   placeholder="2508.18791v2, 2407.01648",
         #   help="Use commas or new lines. Versioned IDs are supported.",
        #)
        # Localized the arXiv ID input label and help text to Arabic(Updated by Imaan Alkhanen)
        arxiv_text = streamlit_backend.text_area(
            "معرفات arXiv",
            value="",
            height=120,
            placeholder="2508.18791v2, 2407.01648",
            #help="Use commas or new lines. Versioned IDs are supported.",
            help="يمكن إدخال المعرفات باستخدام الفواصل أو كل معرف في سطر منفصل ",
        )
    with right:
        
        #project_text = streamlit_backend.text_area(
        #    "Local Projects or Archives",
        #    value="",
        #    height=120,
        #    placeholder=r"D:\path\paper.tar.gz",
        #    help="Supports extracted folders and .zip/.tar/.tar.gz/.tgz archives.",
        #)
        
        # Localized the local project input label and help text to Arabic(Updated by Imaan Alkhanen)
        project_text = streamlit_backend.text_area(
            "المشاريع المحلية أو الملفات المضغوطة",
            value="",
            height=120,
            placeholder=r"D:\path\paper.tar.gz",
            #help="Supports extracted folders and .zip/.tar/.tar.gz/.tgz archives.",
            help="يمكن إدخال مسارات المشاريع المحلية أو الملفات المضغوطة هنا.",
        )

    return {
        "paper_list": split_multivalue_text(arxiv_text),
        "project_items": split_multivalue_text(project_text),
    }


def _append_history(result: Dict[str, Any], params: Dict[str, Any], inputs: Dict[str, List[str]], logs: List[str]) -> None:
    pdfs = _collect_result_pdfs(result)
    output_dir = Path(result["output_dir"])
    history_item = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "params": dict(params),
        "inputs": {
            "paper_list": list(inputs["paper_list"]),
            "project_items": list(inputs["project_items"]),
        },
        "output_dir": str(output_dir),
        "projects": list(result["projects"]),
        "completed_projects": list(result["completed_projects"]),
        "failed_projects": list(result["failed_projects"]),
        "pdfs": pdfs,
        "logs": list(logs[-80:]),
    }
    streamlit_backend.session_state.job_history.insert(0, history_item)
    streamlit_backend.session_state.job_history = streamlit_backend.session_state.job_history[:12]


def _render_result_files(result: Dict[str, Any], params: Dict[str, Any], inputs: Dict[str, List[str]]) -> None:
    output_dir = Path(result["output_dir"])
    completed = result["completed_projects"]
    failed = result["failed_projects"]
    pdfs = [Path(path) for path in _collect_result_pdfs(result)]
    #streamlit_backend.subheader("Results")
    # Localized the results section title  to Arabic(Updated by Imaan Alkhanen)
    streamlit_backend.subheader("النتائج")
    stat_a, stat_b, stat_c = streamlit_backend.columns(3)
    
    #stat_a.metric("Completed", str(len(completed)))
    #stat_b.metric("Failed", str(len(failed)))
    #stat_c.metric("PDF Files", str(len(pdfs)))
    # Localized the results metrics to Arabic(Updated by Imaan Alkhanen)
    stat_a.metric("المكتملة", str(len(completed)))
    stat_b.metric("الفاشلة", str(len(failed)))
    stat_c.metric("ملفات PDF", str(len(pdfs)))

    streamlit_backend.code(str(output_dir), language="text")
    #streamlit_backend.caption("Output directory. Use it directly in File Explorer or your terminal.")
    # Localized the output directory description to Arabic(Updated by Imaan Alkhanen)
    streamlit_backend.caption("مجلد المخرجات. يمكنك فتحه مباشرة باستخدام مستكشف الملفات أو من خلال سطر الأوامر")

    if pdfs:
        #with streamlit_backend.expander("Generated PDF Files", expanded=True):
        # Localized the generated PDF files section heading to Arabic(Updated by Imaan Alkhanen)
        with streamlit_backend.expander("ملفات PDF الناتجة", expanded=True):
            for idx, pdf_path in enumerate(pdfs, start=1):
                streamlit_backend.write(f"{idx}. `{pdf_path.name}`")
                streamlit_backend.code(str(pdf_path), language="text")
                try:
                    with open(pdf_path, "rb") as f:
                        streamlit_backend.download_button(
                            #label=f"Download {pdf_path.name}",
                            # Localized the PDF download button label to Arabic(Updated by Imaan Alkhanen)
                            label=f"تنزيل {pdf_path.name}",
                            data=f.read(),
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            key=f"download_pdf_{idx}_{pdf_path.name}",
                        )
                except OSError:
                    #streamlit_backend.warning(f"Could not read {pdf_path}")
                    # Localized the file read warning message to Arabic(Updated by Imaan Alkhanen)
                    streamlit_backend.warning(f"تعذر قراءة الملف: {pdf_path}")
    else:
        #streamlit_backend.info("No PDF files were found under the output directory yet.")
        # Localized the no-PDF status message to Arabic(Updated by Imaan Alkhanen)
        streamlit_backend.info("لم يتم العثور على أي ملفات PDF في مجلد المخرجات حتى الآن")

    if failed:
        failed_paths = [item["project_dir"] for item in failed]
        retry_payload = {
            "params": dict(params),
            "inputs": {
                "paper_list": [],
                "project_items": failed_paths,
            },
            "all_existing": False,
            #"title": f"Retry {len(failed_paths)} failed project(s)",
            # Localized the retry job title to Arabic(Updated by Imaan Alkhanen)
            "title": f"إعادة محاولة {len(failed_paths)} مشروع فاشل",


        }
        #if streamlit_backend.button("Retry Failed Projects", use_container_width=True):
        # Localized the retry button label to Arabic(Updated by Imaan Alkhanen)
        if streamlit_backend.button("إعادة محاولة المشاريع الفاشلة", use_container_width=True):
            streamlit_backend.session_state.retry_payload = retry_payload
            streamlit_backend.rerun()

    _append_history(result=result, params=params, inputs=inputs, logs=streamlit_backend.session_state.current_run_logs)

## Localized the job history section title and empty-state message to Arabic(Updated by Imaan Alkhanen)
def _render_history() -> None:
    history = streamlit_backend.session_state.job_history
    #streamlit_backend.subheader("Task History")
    streamlit_backend.subheader("سجل المهام")
    if not history:
        streamlit_backend.caption("لا توجد مهام مسجلة في هذه الجلسة حتى الآن")
        return

    for index, item in enumerate(history):
       # label = (
       #     f"{item['timestamp']} | "
       #     f"{len(item['completed_projects'])} ok / {len(item['failed_projects'])} failed | "
       #     f"{Path(item['output_dir']).name}"
       # )
       #Localized the job history entry label to Arabic(Updated by Imaan Alkhanen)
        label = (
                f"{item['timestamp']} | "
                f"{len(item['completed_projects'])} مكتملة / "
                f"{len(item['failed_projects'])} فاشلة | "
                f"{Path(item['output_dir']).name}"
            )
       
        with streamlit_backend.expander(label, expanded=index == 0):
            #streamlit_backend.write("Inputs")
            # Localized the section heading to Arabic(Updated by Imaan Alkhanen)
            streamlit_backend.write("المدخلات")
            if item["inputs"]["paper_list"]:
                streamlit_backend.code("\n".join(item["inputs"]["paper_list"]), language="text")
            if item["inputs"]["project_items"]:
                streamlit_backend.code("\n".join(item["inputs"]["project_items"]), language="text")

            #streamlit_backend.write("Output Directory")
            # Localized the output directory heading to Arabic(Updated by Imaan Alkhanen)
            streamlit_backend.write("مجلد المخرجات")
            streamlit_backend.code(item["output_dir"], language="text")

            if item["pdfs"]:
                #streamlit_backend.write("PDF Files")
                # Localized the PDF files heading to Arabic(Updated by Imaan Alkhanen)
                streamlit_backend.write("ملفات pdf")
                for pdf in item["pdfs"]:
                    streamlit_backend.code(pdf, language="text")

            if item["failed_projects"]:
                failed_dirs = [entry["project_dir"] for entry in item["failed_projects"]]
                #streamlit_backend.write("Failed Projects")
                # Localized the failed projects heading to Arabic(Updated by Imaan Alkhanen)
                streamlit_backend.write("المشاريع الفاشلة")
                streamlit_backend.code("\n".join(failed_dirs), language="text")
                if streamlit_backend.button(
                    #f"Retry Failed Projects from This Run",
                    # Localized the retry failed projects button label to Arabic(Updated by Imaan Alkhanen)
                    f"إعادة محاولة المشاريع الفاشلة من هذا التشغيل",
                    key=f"retry_history_{index}",
                    use_container_width=True,
                ):
                    streamlit_backend.session_state.retry_payload = {
                        "params": dict(item["params"]),
                        "inputs": {
                            "paper_list": [],
                            "project_items": failed_dirs,
                        },
                        "all_existing": False,
                        #"title": f"Retry failed projects from {item['timestamp']}",
                        # Localized the retry job title for failed projects to Arabic(Updated by Imaan Alkhanen)
                        "title": f"إعادة محاولة المشاريع الفاشلة من تشغيل {item['timestamp']}",
                    }
                    streamlit_backend.rerun()

            #streamlit_backend.write("Recent Logs")
            # Localized the recent logs heading to Arabic(Updated by Imaan Alkhanen)
            streamlit_backend.write("أحدث السجلات")
            streamlit_backend.code("\n".join(item["logs"]), language="text")


def _run_streamlit_job(params: Dict[str, Any], inputs: Dict[str, List[str]], title: str) -> None:
    streamlit_backend.subheader(title)
    status_col, stats_col = streamlit_backend.columns([1.6, 1], gap="large")
    with status_col:
        project_text = streamlit_backend.empty()
        stage_text = streamlit_backend.empty()
        overall_bar = streamlit_backend.progress(0.0)
        stage_bar = streamlit_backend.progress(0.0)
    with stats_col:
        stats_placeholder = streamlit_backend.empty()

    log_placeholder = streamlit_backend.empty()
    results_placeholder = streamlit_backend.empty()

    state = {
        "logs": [],
        "raw_buffer": "",
        "project_text": project_text,
        "stage_text": stage_text,
        "overall_bar": overall_bar,
        "stage_bar": stage_bar,
        "completed_projects": 0,
        "total_projects": 0,
    }
    streamlit_backend.session_state.current_run_logs = state["logs"]
    
    #def on_event(event: Dict[str, Any]) -> None:
      #  if event["type"] == "project_start":
       ##    stats_placeholder.metric("Projects", f"{event['index']}/{event['total']}")
         #   project_text.markdown(f"**Project** `{event['index']}/{event['total']}`  `{event['project_name']}`")
          #  if event["total"] > 0:
           #     overall_bar.progress((event["index"] - 1) / event["total"])
        ###  stats_placeholder.metric("Projects", f"{event['index']}/{event['total']}")
           # if event["total"] > 0:
            #    overall_bar.progress(event["index"] / event["total"])
        #elif event["type"] == "project_error":
         #   stats_placeholder.metric("Projects", f"{event['index']}/{event['total']}")
          #  stage_text.markdown(f"**Stage** Error in `{event['project_name']}`: {event['error']}")

    #Localized progress labels and status messages to Arabic(Updated by Imaan Alkhanen)
    def on_event(event: Dict[str, Any]) -> None:
        if event["type"] == "project_start":
            state["total_projects"] = event["total"]
            stats_placeholder.metric("المشاريع", f"{event['index']}/{event['total']}")
            project_text.markdown(f"**المشروع** `{event['index']}/{event['total']}`  `{event['project_name']}`")
            if event["total"] > 0:
                overall_bar.progress((event["index"] - 1) / event["total"])
        elif event["type"] == "project_complete":
            state["completed_projects"] = event["index"]
            stats_placeholder.metric("المشاريع", f"{event['index']}/{event['total']}")
            if event["total"] > 0:
                overall_bar.progress(event["index"] / event["total"])
        elif event["type"] == "project_error":
            stats_placeholder.metric("المشاريع", f"{event['index']}/{event['total']}")
            stage_text.markdown(f"**المرحلة** حدث خطأ في `{event['project_name']}`: {event['error']}")

    overrides = {
        "paper_list": inputs["paper_list"],
        "model": params["model"],
        "url": params["url"],
        "key": params["key"],
        "source": params["source"],
        "output": params["output"],
        "source_language": params["source_language"],
        "target_language": params["target_language"],
        "mode": params["mode"],
        "user_term": params["user_term"],
        "update_term": params["update_term"],
    }

    writer = StreamlitLogWriter(log_placeholder, state)
    previous_backend = get_progress_backend()
    set_progress_backend(streamlit_backend)

    try:
        with redirect_stdout(writer), redirect_stderr(writer):
            result = run_translation(
                config_path=params["config_path"],
                overrides=overrides,
                project_items=inputs["project_items"],
                all_existing=params["all_existing"],
                event_callback=on_event,
            )
    except Exception as exc:
        
        #stage_text.markdown(f"**Stage** Failed: {exc}")
       # results_placeholder.error(f"Run failed: {exc}")
        # Localized the runtime error status and notification messages to Arabic(Updated by Imaan Alkhanen)
        stage_text.markdown(f"**المرحلة** فشل التشغيل: {exc}")
        results_placeholder.error(f"فشل التشغيل: {exc}")
        return
    finally:
        writer.flush()
        set_progress_backend(previous_backend)

    stage_bar.progress(1.0)
    #stage_text.markdown("**Stage** Finished")
    # Localized the completion status message to Arabic(Updated by Imaan Alkhanen)
    stage_text.markdown("**المرحلة** اكتمل التشغيل")
    
    #results_placeholder.success(
     #   f"Completed {len(result['completed_projects'])} project(s), failed {len(result['failed_projects'])}."
    #)
    
    # Localized the translation summary message to Arabic(Updated by Imaan Alkhanen)
    results_placeholder.success(
    f"المشاريع المكتملة: {len(result['completed_projects'])} | المشاريع الفاشلة: {len(result['failed_projects'])}"
    )
    _render_result_files(result=result, params=params, inputs=inputs)


def main() -> None:
    _ensure_session_state()
    _inject_style()
    # Display the hero section with Arabic title and Arabic subtitle (Updated by Imaan Alkhanen)
    streamlit_backend.markdown(
        # """
       # <div class="app-shell">
        #    <div class="hero-title">LaTeXTrans Studio</div>
         #   <p class="hero-subtitle">
          #      Run arXiv or local LaTeX translation jobs with live workflow progress, logs, configurable runtime parameters, and session-level job history.
           # </p>
        #</div>
        #""",

        """
        <div class="app-shell">
            <div class="hero-title">منصة ترجمة Latex</div> 
            <p class="hero-subtitle">
            تشغيل مهام ترجمة ملفات LaTeX من arXiv أو من المشاريع المحلية،
            مع عرض مباشر لتقدم العمل والسجلات وإعدادات التشغيل وسجل المهام.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    default_config_path = "config/default.toml"
    defaults = _load_defaults(default_config_path)
    params = _sidebar_form(defaults)
    inputs = _collect_inputs()
    #streamlit_backend.caption(
     #   "Provide arXiv IDs, local projects, or enable all-existing mode. Results, failed jobs, and recent runs stay visible in this session."
   # )
    
    ## Localized the session description to Arabic (Updated by Imaan Alkhanen)
    streamlit_backend.caption(
        "أدخل معرفات arXiv أو المشاريع المحلية. ستظل النتائج، والمهام التي تعذر تنفيذها، وعمليات التشغيل الأخيرة متاحة طوال هذه الجلسة"
    )

    retry_payload = streamlit_backend.session_state.pop("retry_payload", None)
    if retry_payload:
        _run_streamlit_job(
            params=retry_payload["params"],
            inputs=retry_payload["inputs"],
            title=retry_payload["title"],
        )
        _render_history()
        return
    #run_clicked = streamlit_backend.button("Start Translation", type="primary", use_container_width=True)
    #Main action button (label localized to Arabic) (Updated by Imaan Alkhanen)
    run_clicked = streamlit_backend.button("بدء الترجمة", type="primary", use_container_width=True)
    if run_clicked:
        if not (inputs["paper_list"] or inputs["project_items"] or params["all_existing"]):
            #streamlit_backend.error("No input provided. Add arXiv IDs, local projects, or enable all-existing mode.")
            #Localized the missing input error message to Arabic(Updated by Imaan Alkhanen)
            streamlit_backend.error(
        "لم يتم توفير أي مدخلات. أضف معرفات arXiv أو المشاريع المحلية، أو فعل خيار معالجة جميع المشاريع الموجودة")
        else:
            config_candidate = Path(params["config_path"])
            if not config_candidate.exists():
                #treamlit_backend.error(f"Config file not found: {params['config_path']}")
                #Localized the missing configuration file error message to Arabic(Updated by Imaan Alkhanen)
                streamlit_backend.error(f"لم يتم العثور على ملف الإعدادات: {params['config_path']}")

            else:
                #_run_streamlit_job(params=params, inputs=inputs, title="Current Run")
                #Localized the current run title to Arabic(Updated by Imaan Alkhanen)
                _run_streamlit_job(params=params, inputs=inputs, title="التشغيل الحالي")

    _render_history()


if __name__ == "__main__":
    main()
