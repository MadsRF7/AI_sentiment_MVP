# -------------------------
# SESSION STATE
# -------------------------
if "input_df" not in st.session_state:
    st.session_state["input_df"] = None

if "raw_preview_df" not in st.session_state:
    st.session_state["raw_preview_df"] = None

if "source_file_name" not in st.session_state:
    st.session_state["source_file_name"] = None

if "active_run_id" not in st.session_state:
    st.session_state["active_run_id"] = None

if "scrape_status_message" not in st.session_state:
    st.session_state["scrape_status_message"] = None

if "scrape_status_count" not in st.session_state:
    st.session_state["scrape_status_count"] = None

if "scrape_status_success" not in st.session_state:
    st.session_state["scrape_status_success"] = False
