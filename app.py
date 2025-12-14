import streamlit as st
import pandas as pd
import os
# Ensure pick_nearest_speed.py is in the same folder
from pick_nearest_speed import pick_nearest

# Set page config
st.set_page_config(page_title="Pick Nearest Speed — Table View", layout="wide")

st.title("Pick Nearest Speed — Table View")

# --- File Upload Section ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload OHE CSV")
    ohe_file = st.file_uploader("Select OHE CSV file", type=["csv"], key="ohe")

with col2:
    st.subheader("2. Upload RTIS CSV")
    rtis_file = st.file_uploader("Select RTIS CSV file", type=["csv"], key="rtis")

# --- Parameters Section ---
max_dist = st.number_input("Max distance (m)", value=50.0, step=1.0)

# --- Logic to Run Processing ---
if st.button("Run Processing"):
    if ohe_file is not None and rtis_file is not None:
        try:
            # Streamlit uploads are file-like objects, but your script expects paths.
            # We need to save them temporarily to disk to use your existing function.
            with open("temp_ohe.csv", "wb") as f:
                f.write(ohe_file.getbuffer())
            with open("temp_rtis.csv", "wb") as f:
                f.write(rtis_file.getbuffer())
            
            # Run the pick_nearest function using the temporary file paths
            with st.spinner('Processing... please wait'):
                out_df = pick_nearest(
                    "temp_ohe.csv", 
                    "temp_rtis.csv", 
                    out_csv='__tmp_output.csv', 
                    max_dist_m=max_dist
                )
            
            # Clean up temporary files (optional but good practice)
            # os.remove("temp_ohe.csv")
            # os.remove("temp_rtis.csv")

            # Handle the output
            if isinstance(out_df, pd.DataFrame):
                df = out_df.copy()
            else:
                df = pd.read_csv('__tmp_output.csv')

            # Clean columns as requested
            if 'distance_m' in df.columns:
                df = df.drop(columns=['distance_m'])
            
            # Save to session state so it persists across re-runs
            st.session_state['df'] = df
            st.success("Processing Complete!")

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please upload both CSV files first.")

# --- Results & Search Section ---
if 'df' in st.session_state:
    df = st.session_state['df']
    
    st.divider()
    st.subheader("Results")

    # Search functionality
    search_query = st.text_input("Search OHEMas:", "")

    if search_query:
        # Filter the dataframe based on search
        filtered_df = df[df['OHEMas'].astype(str).str.lower().str.contains(search_query.lower())]
    else:
        filtered_df = df

    # Display Dataframe (replaces Treeview)
    st.dataframe(filtered_df, use_container_width=True)

    # Download Button (replaces Save CSV)
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name='output_nearest_speed.csv',
        mime='text/csv',
    )
