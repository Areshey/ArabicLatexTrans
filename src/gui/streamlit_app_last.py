import io
import re
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import streamlit as streamlit_backend
import toml

from src.runtime import run_translation, split_multivalue_text
from src.utils.progress import get_progress_backend, set_progress_backend, set_status_language


# =====================================================================
# Central bilingual label store. Every user-facing string in this file
# (outside of _sidebar_form(), which already has its own working
# English/Arabic dict) is looked up through _t(key) below, which reads
# the current UI language from session_state. This lets every function
# in the file react to the "Language / اللغة" dropdown without needing
# ui_language threaded through every function signature.
# =====================================================================
LABELS = {
    "English": {
        "page_title": "Latex Translation Platform",
        "hero_title": "Latex Translation Platform",
        "hero_subtitle": "Run LaTeX file translation jobs from arXiv or local projects, with live workflow progress, logs, and run configuration.",
        "session_caption": "Enter arXiv IDs or local projects. Results, failed jobs, and recent runs stay visible throughout this session.",
        "start_button": "Start Translation",
        "no_input_error": "No input provided. Add arXiv IDs or local projects, or enable the process-all-existing-projects option.",
        "config_not_found_error": "Config file not found: {path}",
        "current_run_title": "Current Run",

        "arxiv_ids_label": "arXiv IDs",
        "arxiv_ids_help": "Use commas or new lines. Versioned IDs are supported.",
        "local_projects_label": "Local Projects or Archives",
        "local_projects_help": "Supports extracted folders and .zip/.tar/.tar.gz/.tgz archives.",

        "results_subheader": "Results",
        "metric_completed": "Completed",
        "metric_failed": "Failed",
        "metric_pdf_files": "PDF Files",
        "output_dir_caption": "Output directory. Use it directly in File Explorer or your terminal.",
        "generated_pdfs_expander": "Generated PDF Files",
        "download_button": "Download {name}",
        "read_error_warning": "Could not read {path}",
        "no_pdfs_info": "No PDF files were found under the output directory yet.",
        "retry_failed_title": "Retry {count} failed project(s)",
        "retry_failed_button": "Retry Failed Projects",

        "history_subheader": "Task History",
        "history_empty_caption": "No jobs recorded in this session yet.",
        "history_entry_label": "{timestamp} | {completed} ok / {failed} failed | {output_dir}",
        "history_inputs_label": "Inputs",
        "history_output_dir_label": "Output Directory",
        "history_pdf_files_label": "PDF Files",
        "history_failed_projects_label": "Failed Projects",
        "history_retry_button": "Retry Failed Projects from This Run",
        "history_retry_title": "Retry failed projects from {timestamp}",
        "history_recent_logs_label": "Recent Logs",

        "project_progress_label": "Project",
        "stage_progress_label": "Stage",
        "stats_projects_label": "Projects",
        "stage_error_label": "Error in `{name}`: {error}",
        "run_failed_stage": "Failed: {error}",
        "run_failed_notice": "Run failed: {error}",
        "stage_finished": "Finished",
        "run_summary": "Completed {completed} project(s), failed {failed}.",
    },
    "Arabic": {
        "page_title": "منصة ترجمة Latex",
        "hero_title": "منصة ترجمة Latex",
        "hero_subtitle": "تشغيل مهام ترجمة ملفات LaTeX من arXiv أو من المشاريع المحلية، مع عرض مباشر لتقدم العمل والسجلات وإعدادات التشغيل وسجل المهام.",
        "session_caption": "أدخل معرفات arXiv أو المشاريع المحلية. ستظل النتائج، والمهام التي تعذر تنفيذها، وعمليات التشغيل الأخيرة متاحة طوال هذه الجلسة",
        "start_button": "بدء الترجمة",
        "no_input_error": "لم يتم توفير أي مدخلات. أضف معرفات arXiv أو المشاريع المحلية، أو فعل خيار معالجة جميع المشاريع الموجودة",
        "config_not_found_error": "لم يتم العثور على ملف الإعدادات: {path}",
        "current_run_title": "التشغيل الحالي",

        "arxiv_ids_label": "معرفات arXiv",
        "arxiv_ids_help": "يمكن إدخال المعرفات باستخدام الفواصل أو كل معرف في سطر منفصل",
        "local_projects_label": "المشاريع المحلية أو الملفات المضغوطة",
        "local_projects_help": "يمكن إدخال مسارات المشاريع المحلية أو الملفات المضغوطة هنا.",

        "results_subheader": "النتائج",
        "metric_completed": "المكتملة",
        "metric_failed": "الفاشلة",
        "metric_pdf_files": "ملفات PDF",
        "output_dir_caption": "مجلد المخرجات. يمكنك فتحه مباشرة باستخدام مستكشف الملفات أو من خلال سطر الأوامر",
        "generated_pdfs_expander": "ملفات PDF الناتجة",
        "download_button": "تنزيل {name}",
        "read_error_warning": "تعذر قراءة الملف: {path}",
        "no_pdfs_info": "لم يتم العثور على أي ملفات PDF في مجلد المخرجات حتى الآن",
        "retry_failed_title": "إعادة محاولة {count} مشروع فاشل",
        "retry_failed_button": "إعادة محاولة المشاريع الفاشلة",

        "history_subheader": "سجل المهام",
        "history_empty_caption": "لا توجد مهام مسجلة في هذه الجلسة حتى الآن",
        "history_entry_label": "{timestamp} | {completed} مكتملة / {failed} فاشلة | {output_dir}",
        "history_inputs_label": "المدخلات",
        "history_output_dir_label": "مجلد المخرجات",
        "history_pdf_files_label": "ملفات pdf",
        "history_failed_projects_label": "المشاريع الفاشلة",
        "history_retry_button": "إعادة محاولة المشاريع الفاشلة من هذا التشغيل",
        "history_retry_title": "إعادة محاولة المشاريع الفاشلة من تشغيل {timestamp}",
        "history_recent_logs_label": "أحدث السجلات",

        "project_progress_label": "المشروع",
        "stage_progress_label": "المرحلة",
        "stats_projects_label": "المشاريع",
        "stage_error_label": "حدث خطأ في `{name}`: {error}",
        "run_failed_stage": "فشل التشغيل: {error}",
        "run_failed_notice": "فشل التشغيل: {error}",
        "stage_finished": "اكتمل التشغيل",
        "run_summary": "المشاريع المكتملة: {completed} | المشاريع الفاشلة: {failed}",
    },
}


def _current_ui_language() -> str:
    """Current UI language, defaulting to Arabic (matches the sidebar's own default)."""
    return streamlit_backend.session_state.get("ui_language", "Arabic")


def _t(key: str, **kwargs) -> str:
    """Look up a label in the current UI language, with optional .format() kwargs."""
    text = LABELS[_current_ui_language()][key]
    return text.format(**kwargs) if kwargs else text


def _collect_result_pdfs(result: Dict[str, Any]) -> List[str]:
    output_dir = Path(result["output_dir"])
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
            self.state["project_text"].markdown(f"**{_t('project_progress_label')}** `{current}/{total}`  `{name}`")
            if total > 0:
                self.state["overall_bar"].progress((current - 1) / total)
            return

        progress_match = re.search(r"(\d+(?:\.\d+)?)%", line)
        if progress_match:
            percent = min(100.0, max(0.0, float(progress_match.group(1))))
            self.state["stage_bar"].progress(percent / 100.0)
            self.state["stage_text"].markdown(f"**{_t('stage_progress_label')}** {line}")
            return

        if line.startswith("[") or "Error processing project" in line or "Successfully" in line:
            self.state["stage_text"].markdown(f"**{_t('stage_progress_label')}** {line}")


def _load_defaults(config_path: str) -> Dict[str, Any]:
    try:
        return toml.load(config_path)
    except Exception:
        return {}


def _ensure_session_state() -> None:
    streamlit_backend.session_state.setdefault("job_history", [])
    streamlit_backend.session_state.setdefault("retry_failed_only", False)
    streamlit_backend.session_state.setdefault("retry_payload", None)
    streamlit_backend.session_state.setdefault("ui_language", "Arabic")


def _set_page_config() -> None:
    # Must run once, before any other Streamlit command. Page title uses
    # whatever UI language was set on the PREVIOUS run (default Arabic on
    # first load) -- a one-run lag on the browser tab title only, since
    # set_page_config cannot be deferred until after the sidebar renders.
    streamlit_backend.set_page_config(
        page_title=_t("page_title"),
        page_icon="L",
        layout="wide",
    )


def _inject_css(ui_language: str) -> None:
    rtl_block = """
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
    """ if ui_language == "Arabic" else ""

    streamlit_backend.markdown(
        f"""
        <style>
        /* Direction rules only applied for Arabic */
        {rtl_block}
        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(245, 173, 92, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(26, 96, 107, 0.18), transparent 24%),
                linear-gradient(180deg, #f7f2ea 0%, #f1ede4 100%);
        }}
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        .app-shell {{
            padding: 1.25rem 1.5rem;
            border-radius: 24px;
            background: rgba(255, 252, 247, 0.84);
            border: 1px solid rgba(46, 56, 64, 0.08);
            box-shadow: 0 18px 60px rgba(67, 51, 32, 0.10);
            backdrop-filter: blur(12px);
        }}
        .hero-title {{
            font-size: 2.2rem;
            font-weight: 700;
            line-height: 1.05;
            color: #17323b;
            margin-bottom: 0.35rem;
        }}
        .hero-subtitle {{
            color: #5f5c53;
            font-size: 1rem;
            margin-bottom: 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_form(defaults: Dict[str, Any]) -> Dict[str, Any]:
    llm_defaults = defaults.get("llm_config", {})
    # UI language selector
    ui_language = streamlit_backend.sidebar.selectbox(
        "Language / اللغة",
        options=["Arabic", "English"],
        index=0 if _current_ui_language() == "Arabic" else 1,
    )
    streamlit_backend.session_state["ui_language"] = ui_language

    # === Sidebar Translation Mapping ===
    labels = {
        "English": {
            "header": "Run Configuration",
            "config_path": "Config Path",
            "source_lang": "Source Language",
            "target_lang": "Target Language",
            "model": "Model",
            "base_url": "Base URL",
            "api_key": "API Key",
            "tex_dir": "TeX Source Dir",
            "output_dir": "Output Dir",
            "mode": "Mode",
            "update_terms": "Update Terms",
            "all_existing": "Process All Existing Projects",
            "user_terms": "User Terms",
            "help_text": "Optional terminology guidance passed through the existing config field.",
        },
        "Arabic": {
            "header": "إعدادات التشغيل",
            "config_path": "مسار ملف الإعدادات",
            "source_lang": "لغة المصدر",
            "target_lang": "اللغة المستهدفة",
            "model": "النموذج",
            "base_url": "رابط واجهة البرمجة (API)",
            "api_key": "مفتاح واجهة البرمجة (API Key)",
            "tex_dir": "مجلد ملفات LaTeX",
            "output_dir": "مجلد المخرجات",
            "mode": "وضع التشغيل",
            "update_terms": "تحديث المصطلحات",
            "all_existing": "معالجة جميع المشاريع الموجودة",
            "user_terms": "المصطلحات الخاصة بالمستخدم",
            "help_text": "إرشادات اختيارية للمصطلحات يتم تمريرها عبر حقل الإعدادات الحالي.",
        },
    }
    lang_labels = labels[ui_language]
    # Dynamic Sidebar Fields
    streamlit_backend.sidebar.header(lang_labels["header"])
    config_path = streamlit_backend.sidebar.text_input(lang_labels["config_path"], "config/default.toml")
    source_language = streamlit_backend.sidebar.text_input(lang_labels["source_lang"], defaults.get("source_language", "en"))
    target_language = streamlit_backend.sidebar.text_input(lang_labels["target_lang"], defaults.get("target_language", "ar"))
    model = streamlit_backend.sidebar.text_input(lang_labels["model"], llm_defaults.get("model", ""))
    base_url = streamlit_backend.sidebar.text_input(lang_labels["base_url"], llm_defaults.get("base_url", ""))
    api_key = streamlit_backend.sidebar.text_input(lang_labels["api_key"], llm_defaults.get("api_key", ""), type="password")
    tex_source_dir = streamlit_backend.sidebar.text_input(lang_labels["tex_dir"], defaults.get("tex_sources_dir", "tex source"))
    output_dir = streamlit_backend.sidebar.text_input(lang_labels["output_dir"], defaults.get("output_dir", "outputs"))

    if ui_language == "Arabic":
        mode_options = {"0 - عادي": 0, "1 - إعادة محاولة الأخطاء": 1, "2 - بديل": 2}
    else:
        mode_options = {"0 - Normal": 0, "1 - Retry Errors": 1, "2 - Alt": 2}
    selected_mode = streamlit_backend.sidebar.selectbox(lang_labels["mode"], list(mode_options.keys()), index=0)
    update_term = streamlit_backend.sidebar.checkbox(
        lang_labels["update_terms"],
        value=str(defaults.get("update_term", "False")) == "True",
    )
    all_existing = streamlit_backend.sidebar.checkbox(lang_labels["all_existing"], value=False)
    user_term = streamlit_backend.sidebar.text_area(
        lang_labels["user_terms"],
        defaults.get("user_term", ""),
        height=120,
        help=lang_labels["help_text"],
    )

    return {
        "config_path": config_path,
        "source_language": source_language.strip() or "en",
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


def _collect_inputs() -> Dict[str, List[str]]:
    left, right = streamlit_backend.columns([1.15, 0.85], gap="large")
    with left:
        arxiv_text = streamlit_backend.text_area(
            _t("arxiv_ids_label"),
            value="",
            height=120,
            placeholder="2508.18791v2, 2407.01648",
            help=_t("arxiv_ids_help"),
        )
    with right:
        project_text = streamlit_backend.text_area(
            _t("local_projects_label"),
            value="",
            height=120,
            placeholder=r"D:\path\paper.tar.gz",
            help=_t("local_projects_help"),
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

    streamlit_backend.subheader(_t("results_subheader"))
    stat_a, stat_b, stat_c = streamlit_backend.columns(3)
    stat_a.metric(_t("metric_completed"), str(len(completed)))
    stat_b.metric(_t("metric_failed"), str(len(failed)))
    stat_c.metric(_t("metric_pdf_files"), str(len(pdfs)))

    streamlit_backend.code(str(output_dir), language="text")
    streamlit_backend.caption(_t("output_dir_caption"))

    if pdfs:
        with streamlit_backend.expander(_t("generated_pdfs_expander"), expanded=True):
            for idx, pdf_path in enumerate(pdfs, start=1):
                streamlit_backend.write(f"{idx}. `{pdf_path.name}`")
                streamlit_backend.code(str(pdf_path), language="text")
                try:
                    with open(pdf_path, "rb") as f:
                        streamlit_backend.download_button(
                            label=_t("download_button", name=pdf_path.name),
                            data=f.read(),
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            key=f"download_pdf_{idx}_{pdf_path.name}",
                        )
                except OSError:
                    streamlit_backend.warning(_t("read_error_warning", path=pdf_path))
    else:
        streamlit_backend.info(_t("no_pdfs_info"))

    if failed:
        failed_paths = [item["project_dir"] for item in failed]
        retry_payload = {
            "params": dict(params),
            "inputs": {
                "paper_list": [],
                "project_items": failed_paths,
            },
            "all_existing": False,
            "title": _t("retry_failed_title", count=len(failed_paths)),
        }
        if streamlit_backend.button(_t("retry_failed_button"), use_container_width=True):
            streamlit_backend.session_state.retry_payload = retry_payload
            streamlit_backend.rerun()

    _append_history(result=result, params=params, inputs=inputs, logs=streamlit_backend.session_state.current_run_logs)


def _render_history() -> None:
    history = streamlit_backend.session_state.job_history
    streamlit_backend.subheader(_t("history_subheader"))
    if not history:
        streamlit_backend.caption(_t("history_empty_caption"))
        return

    for index, item in enumerate(history):
        label = _t(
            "history_entry_label",
            timestamp=item["timestamp"],
            completed=len(item["completed_projects"]),
            failed=len(item["failed_projects"]),
            output_dir=Path(item["output_dir"]).name,
        )
        with streamlit_backend.expander(label, expanded=index == 0):
            streamlit_backend.write(_t("history_inputs_label"))
            if item["inputs"]["paper_list"]:
                streamlit_backend.code("\n".join(item["inputs"]["paper_list"]), language="text")
            if item["inputs"]["project_items"]:
                streamlit_backend.code("\n".join(item["inputs"]["project_items"]), language="text")

            streamlit_backend.write(_t("history_output_dir_label"))
            streamlit_backend.code(item["output_dir"], language="text")

            if item["pdfs"]:
                streamlit_backend.write(_t("history_pdf_files_label"))
                for pdf in item["pdfs"]:
                    streamlit_backend.code(pdf, language="text")

            if item["failed_projects"]:
                failed_dirs = [entry["project_dir"] for entry in item["failed_projects"]]
                streamlit_backend.write(_t("history_failed_projects_label"))
                streamlit_backend.code("\n".join(failed_dirs), language="text")
                if streamlit_backend.button(
                    _t("history_retry_button"),
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
                        "title": _t("history_retry_title", timestamp=item["timestamp"]),
                    }
                    streamlit_backend.rerun()

            streamlit_backend.write(_t("history_recent_logs_label"))
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

    def on_event(event: Dict[str, Any]) -> None:
        if event["type"] == "project_start":
            state["total_projects"] = event["total"]
            stats_placeholder.metric(_t("stats_projects_label"), f"{event['index']}/{event['total']}")
            project_text.markdown(f"**{_t('project_progress_label')}** `{event['index']}/{event['total']}`  `{event['project_name']}`")
            if event["total"] > 0:
                overall_bar.progress((event["index"] - 1) / event["total"])
        elif event["type"] == "project_complete":
            state["completed_projects"] = event["index"]
            stats_placeholder.metric(_t("stats_projects_label"), f"{event['index']}/{event['total']}")
            if event["total"] > 0:
                overall_bar.progress(event["index"] / event["total"])
        elif event["type"] == "project_error":
            stats_placeholder.metric(_t("stats_projects_label"), f"{event['index']}/{event['total']}")
            stage_text.markdown(f"**{_t('stage_progress_label')}** {_t('stage_error_label', name=event['project_name'], error=event['error'])}")

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
    set_status_language("ar" if _current_ui_language() == "Arabic" else "en")  # backend status messages now follow the UI language dropdown, not the paper's target_language

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
        stage_text.markdown(f"**{_t('stage_progress_label')}** {_t('run_failed_stage', error=exc)}")
        results_placeholder.error(_t("run_failed_notice", error=exc))
        return
    finally:
        writer.flush()
        set_progress_backend(previous_backend)

    stage_bar.progress(1.0)
    stage_text.markdown(f"**{_t('stage_progress_label')}** {_t('stage_finished')}")

    results_placeholder.success(
        _t("run_summary", completed=len(result["completed_projects"]), failed=len(result["failed_projects"]))
    )
    _render_result_files(result=result, params=params, inputs=inputs)


def main() -> None:
    _ensure_session_state()
    _set_page_config()

    default_config_path = "config/default.toml"
    defaults = _load_defaults(default_config_path)
    params = _sidebar_form(defaults)
    ui_language = _current_ui_language()

    _inject_css(ui_language)

    streamlit_backend.markdown(
        f"""
        <div class="app-shell">
        <div class="hero-title">{_t("hero_title")}</div>
        <p class="hero-subtitle">
        {_t("hero_subtitle")}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    inputs = _collect_inputs()
    streamlit_backend.caption(_t("session_caption"))

    retry_payload = streamlit_backend.session_state.pop("retry_payload", None)
    if retry_payload:
        _run_streamlit_job(
            params=retry_payload["params"],
            inputs=retry_payload["inputs"],
            title=retry_payload["title"],
        )
        _render_history()
        return

    run_clicked = streamlit_backend.button(_t("start_button"), type="primary", use_container_width=True)
    if run_clicked:
        if not (inputs["paper_list"] or inputs["project_items"] or params["all_existing"]):
            streamlit_backend.error(_t("no_input_error"))
        else:
            config_candidate = Path(params["config_path"])
            if not config_candidate.exists():
                streamlit_backend.error(_t("config_not_found_error", path=params["config_path"]))
            else:
                _run_streamlit_job(params=params, inputs=inputs, title=_t("current_run_title"))

    _render_history()


if __name__ == "__main__":
    main()
