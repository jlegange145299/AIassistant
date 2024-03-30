
from pathlib import Path
from openai import OpenAI
import time
import streamlit as st
from PIL import Image
import threading
import pydub
from pydub.playback import play
import os
import requests
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

avatarlist = {
    "Male": "https://photosfordidd.s3.eu-central-1.amazonaws.com/alice.png",
    "Female": "https://photosfordidd.s3.eu-central-1.amazonaws.com/alice.png"
}

    # Function to generate video based on the prompt and avatar selection
         
def main():
    #processed_response = "Hello how are you - how can I help today?" 
    
    st.set_page_config(
        page_title="Cigna AI Assistant",
        page_icon="📚",
        layout="wide"
    ) 
    
    api_key = st.secrets["OPENAI_API_KEY"]
    assistant_id = st.secrets["ASSISTANT_ID"]
    
    col1,col2 = st.columns(2)       
        # Images
        #with col2:
        
    with col1:                    
         image_path = "https://photosfordidd.s3.eu-central-1.amazonaws.com/2.png"
         st.image(image_path, caption='',width=300)    
        
    st.sidebar.header("Press the play icon to say hello")
    video_path = "https://photosfordidd.s3.eu-central-1.amazonaws.com/video.mp4"        
    st.sidebar.video(video_path,start_time=0)    
        
    image2_path = "https://photosfordidd.s3.eu-central-1.amazonaws.com/new.png"
    st.sidebar.image(image2_path, caption='',width=300)
        
    add_selectbox = st.sidebar.selectbox(
        'How often would you like to be contacted?',
        ('Daily', 'Weekly', 'Monthly','Never')
    )
    slider_value = st.sidebar.slider("How satisfied out of 10 were you with your last Cigna interaction?", 0, 5, 10)
     

    # Initiate st.session_state
    st.session_state.client = OpenAI(api_key=api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    if "start_chat" not in st.session_state:
        st.session_state.start_chat = False

    if st.session_state.client:
        st.session_state.start_chat = True
    
    if "processed_response" not in st.session_state:
                st.session_state.sprocessed_response = []

    if st.session_state.start_chat:
        # Display existing messages in the chat
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Accept user input
        if prompt := st.chat_input("Hello how can I help?"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)

            # Create a thread
            st.session_state.thread = st.session_state.client.beta.threads.create()

            # Add a Message to the thread
            st.session_state.client.beta.threads.messages.create(
                thread_id=st.session_state.thread.id,
                role="user",
                content=prompt,
            )

            # As of now, assistant and thread are not associated to eash other
            # You need to create a run in order to tell the assistant at which thread to look at
            run = st.session_state.client.beta.threads.runs.create(
                thread_id=st.session_state.thread.id,
                assistant_id=assistant_id,
            )

            # with while loop continuously check the status of a run until it neither 'queued' nor 'in progress'
            def wait_for_complete(run, thread):
                while run.status == "queued" or run.status == "in_progress":
                    run = st.session_state.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id,
                    )
                    time.sleep(0.5)
                return run

            run = wait_for_complete(run, st.session_state.thread)

            # once the run has completed, list the messages in the thread -> they are ordered in reverse chronological order
            replies = st.session_state.client.beta.threads.messages.list(
                thread_id=st.session_state.thread.id
            )

            # This function will parse citations and make them readable
            def process_replies(replies):
                citations = []

                # Iterate over all replies
                for r in replies:
                    if r.role == "assistant":
                        message_content = r.content[0].text
                        annotations = message_content.annotations

                        # Iterate over the annotations and add footnotes
                        for index, annotation in enumerate(annotations):
                            # Replace the text with a footnote
                            message_content.value = message_content.value.replace(
                                annotation.text, f" [{index}]"
                            )

                            # Gather citations based on annotation attributes
                            if file_citation := getattr(
                                annotation, "file_citation", None
                            ):
                                cited_file = st.session_state.client.files.retrieve(
                                    file_citation.file_id
                                )
                                citations.append(
                                    f"[{index}] {file_citation.quote} from {cited_file.filename}"
                                )
                            elif file_path := getattr(annotation, "file_path", None):
                                cited_file = st.session_state.client.files.retrieve(
                                    file_path.file_id
                                )
                                citations.append(
                                    f"[{index}] Click <here> to download {cited_file.filename}"
                                )

                # Combine message content and citations
                full_response = message_content.value + "\n" + "\n".join(citations)
                return full_response

            # Add the processed response to session state          
            processed_response = process_replies(replies) 
            st.session_state.messages.append(
                 {"role": "assistant", "content": processed_response}
                )           
                
            st.text(processed_response)
            
        def generate_video(prompt, avatar_url, gender):
                url = "https://api.d-id.com/talks"
                headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization" : "Basic YW1GamNYVmxjMnhsWjNKaGJtZGxRR2R0WVdsc0xtTnZiUTpuNjdqWmdMcXR0VUhJbjJ6dTVlcTI="
            }
                if gender == "Female":
                    payload = {
                        "script": {
                            "type": "text",
                            "subtitles": "false",
                            "provider": {
                                "type": "microsoft",
                                "voice_id": "en-US-JaneNeural"
                            },
                            "ssml": "false",
                            "input":prompt
                        },
                        "config": {
                            "fluent": "false",
                            "pad_audio": "0.0",
                            "stitch": "true"
                        },
                        "source_url": avatar_url
                    }

                if gender == "Male":
                    payload = {
                        "script": {
                            "type": "text",
                            "subtitles": "false",
                            "provider": {
                                "type": "microsoft",
                                "voice_id": "en-US-JennyNeural"
                            },
                            "ssml": "false",
                            "input":prompt
                        },
                        "config": {
                            "fluent": "false",
                            "pad_audio": "0.0",
                            "stitch": "true"
                        },
                        "source_url": avatar_url
                    }
    
                try:
                    response = requests.post(url, json=payload, headers=headers)
                    if response.status_code == 201:
                        print(response.text)
                        res = response.json()
                        id = res["id"]
                        status = "created"
                        while status == "created":
                            getresponse =  requests.get(f"{url}/{id}", headers=headers)
                            print(getresponse)
                            if getresponse.status_code == 200:
                                status = res["status"]
                                res = getresponse.json()
                                print(res)
                                if res["status"] == "done":
                                    video_url =  res["result_url"]
                                else:
                                    time.sleep(10)
                            else:
                                status = "error"
                                video_url = "error"
                    else:
                        video_url = "error"   
                except Exception as e:
                    print(e)      
                    video_url = "error"          
        
                return video_url 
        video_url = generate_video("Hello", video_url, "Female")          
        st.video(video_url)
            # Text prompt input
            #prompt = st.sidebar.text_area("Enter Text Prompt", processed_response) 
                         
        # Dropdown box for avatar selection
            #avatar_options = ["Male", "Female"]
        #avatar_selection = st.sidebar.selectbox("Choose Avatar", avatar_options)
            #avatar_selection = "Female"        
            #avatar_url = avatarlist[avatar_selection]

        # Generate video button
            #if st.sidebar.button("Generate Video"):
                    #st.text("Generating video...")
            #try:
                            #video_url = generate_video(prompt, avatar_url, avatar_selection)  # Call your video generation function here
                            #if video_url!= "error":
                             #with col2: 
                                #st.text("Video generated!")
                    # Placeholder for displaying generated video
                                #st.subheader("Generated Video")
                                #st.video(video_url) # Replace with the actual path
                            #else:
                             #st.text("Sorry... Try again")
            #except Exception as e:
                    #print(e)
            #st.text("Sorry... Try again")           
                
if __name__ == "__main__":
    main()
