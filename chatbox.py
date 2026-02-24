import streamlit as st
from openai import OpenAI
import re
import time

# 1. CẤU HÌNH API (Lấy từ Secrets để bảo mật)
# Nếu bạn dán thẳng Key vào code thì thay: st.secrets["OPENAI_API_KEY"] bằng "KEY_CỦA_BẠN"
try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    API_KEY = "SỬ_DỤNG_KEY_CỦA_BẠN_TẠI_ĐÂY"

client = OpenAI(api_key=API_KEY)

st.set_page_config(page_title="Trợ Lý Tâm Linh - Chùa Online", layout="centered")

# 2. GIAO DIỆN CHÙA (CSS)
st.markdown("""
    <style>
    .stApp { background-color: #FFF9E6; }
    [data-testid="stSidebar"] { background-color: #F4D03F; color: #5D4037; }
    h1, h2, h3, p, span { color: #5D4037 !important; font-family: 'serif'; }
    .stChatMessage { background-color: #FFFFFF; border: 1px solid #F1C40F; border-radius: 15px; }
    .lotus-header { text-align: center; font-size: 50px; color: #E67E22; margin-bottom: -10px; }
    </style>
""", unsafe_allow_html=True)

# Khởi tạo Session State
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "assistant_id" not in st.session_state:
    st.session_state["assistant_id"] = None

# Hàm hiển thị thông minh
def smart_display(text):
    clean_text = re.sub(r'【.*?】', '', text)
    keyword_match = re.search(r'IMAGE_KEYWORD:\s*([\w_]+)', clean_text)
    final_text = clean_text.split("IMAGE_KEYWORD:")[0]
    st.markdown(final_text)
    if keyword_match:
        keyword = keyword_match.group(1)
        img_url = f"https://image.pollinations.ai/prompt/{keyword}_buddhism_zen_peaceful?width=800&height=500&nologo=true"
        st.image(img_url, caption=f"Hình ảnh: {keyword.replace('_', ' ')}")

st.markdown('<div class="lotus-header">🪷</div>', unsafe_allow_html=True)
st.title("A Di Đà Phật - Trợ Lý Học Tu")

# 3. SIDEBAR
with st.sidebar:
    st.markdown("## ☸️ Phật Pháp Nhiệm Màu")
    uploaded_file = st.file_uploader("Tải lên Kinh sách (PDF/Docx)", type=['pdf', 'txt', 'docx'])
    
    if uploaded_file and st.session_state["assistant_id"] is None:
        with st.spinner("Đang thỉnh tri thức vào AI..."):
            try:
                # 1. Tải file
                file_obj = client.files.create(file=uploaded_file, purpose='assistants')
                
                # 2. Tạo Vector Store (Sử dụng cú pháp chuẩn v2)
                vector_store = client.beta.vector_stores.create(name="TempleStore")
                
                # 3. Chờ file được xử lý và add vào store
                client.beta.vector_stores.files.create_and_poll(
                    vector_store_id=vector_store.id, file_id=file_obj.id
                )
                
                # 4. Tạo Assistant
                instruction_prompt = """
                Bạn là một vị Trợ lý Tâm linh điềm đạm. 
                - Xưng hô: A Di Đà Phật, Đạo hữu, Phật tử.
                - Trả lời dựa trên file Kinh sách. 
                - Luôn kết thúc bằng 'IMAGE_KEYWORD: [từ khóa tiếng Anh]' để minh họa.
                """
                assist = client.beta.assistants.create(
                    name="Sư Thầy AI",
                    instructions=instruction_prompt,
                    tools=[{"type": "file_search"}],
                    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
                    model="gpt-4o"
                )
                st.session_state["assistant_id"] = assist.id
                st.success("A Di Đà Phật, Kinh sách đã nạp xong!")
            except Exception as e:
                st.error(f"Lỗi hệ thống: {e}")

    if st.button("Xóa lịch sử hội thoại"):
        st.session_state["messages"] = []
        st.rerun()

# 4. CHAT
for m in st.session_state["messages"]:
    with st.chat_message(m["role"], avatar="🙏" if m["role"]=="user" else "🪷"):
        if m["role"] == "user":
            st.markdown(m["content"])
        else:
            smart_display(m["content"])

if prompt := st.chat_input("Bạch Thầy, con có điều chưa rõ..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🙏"):
        st.markdown(prompt)

    if not st.session_state["assistant_id"]:
        st.info("Quý Phật tử vui lòng chờ trong giây lát để tải Kinh sách ở bên trái.")
    else:
        with st.chat_message("assistant", avatar="🪷"):
            with st.spinner("Đang quán chiếu..."):
                thread = client.beta.threads.create(messages=[{"role": "user", "content": prompt}])
                run = client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id, assistant_id=st.session_state["assistant_id"]
                )
                if run.status == 'completed':
                    messages = client.beta.threads.messages.list(thread_id=thread.id)
                    ans = messages.data[0].content[0].text.value
                    st.session_state["messages"].append({"role": "assistant", "content": ans})
                    smart_display(ans)
                    st.rerun()
