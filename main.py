import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="RaterHub History Analyzer", layout="wide")

st.title("RaterHub History Analyzer")
st.markdown("Upload your browser history CSV file and specify the month to extract RaterHub tasks.")

# Month selection
current_year = datetime.now().year
months = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
]

col1, col2 = st.columns(2)
with col1:
    selected_month = st.selectbox("Select Month", months)
with col2:
    selected_year = st.selectbox("Select Year", [current_year, current_year-1])

# File uploader
uploaded_file = st.file_uploader("Upload browser history CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        # Read the CSV file
        df = pd.read_csv(uploaded_file)
        
        # Check if required columns exist
        required_columns = ["order", "id", "date", "time", "title", "url"]
        if not all(col in df.columns for col in required_columns):
            st.error("The uploaded file is missing required columns. Please ensure it contains: order, id, date, time, title, url")
        else:
            # Show preview of uploaded data
            st.subheader("Preview of Uploaded Data")
            st.dataframe(df.head())
            
            # Convert month name to number
            month_num = months.index(selected_month) + 1
            
            # Filter by the selected month and year
            df['date'] = pd.to_datetime(df['date'])
            filtered_df = df[
                (df['date'].dt.month == month_num) & 
                (df['date'].dt.year == selected_year)
            ]
            
            # Filter for RaterHub URLs
            raterhub_df = filtered_df[filtered_df['url'].str.contains('raterhub', case=False, na=False)]
            
            if raterhub_df.empty:
                st.warning(f"No RaterHub URLs found for {selected_month} {selected_year}")
            else:
                # Extract Task IDs from URLs
                def extract_task_id(url):
                    match = re.search(r'taskIds=(\d+)', url)
                    return match.group(1) if match else None
                
                raterhub_df['task_id'] = raterhub_df['url'].apply(extract_task_id)
                
                # Convert GMT+7 to Pacific Time
                def convert_to_pacific(date, time):
                    try:
                        # Create datetime from date and time
                        dt_str = f"{date.strftime('%Y-%m-%d')} {time}"
                        dt_gmt7 = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                        
                        # Assume original time is GMT+7
                        gmt7 = pytz.timezone('Asia/Bangkok')  # GMT+7
                        pacific = pytz.timezone('US/Pacific')
                        
                        # Localize to GMT+7, then convert to Pacific
                        dt_gmt7 = gmt7.localize(dt_gmt7)
                        dt_pacific = dt_gmt7.astimezone(pacific)
                        
                        return dt_pacific.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        return f"Error converting time: {e}"
                
                raterhub_df['pacific_time'] = raterhub_df.apply(
                    lambda row: convert_to_pacific(row['date'], row['time']), axis=1
                )
                
                # Prepare final dataframe
                result_df = raterhub_df[['pacific_time', 'url', 'task_id']].copy()
                result_df.columns = ['Date (Pacific Time)', 'URL', 'Task ID']
                
                # Remove rows with None task IDs
                result_df = result_df.dropna(subset=['Task ID'])
                
                # Sort by date
                result_df['Date (Pacific Time)'] = pd.to_datetime(result_df['Date (Pacific Time)'])
                
                # Remove duplicates, keeping the first occurrence of each Task ID
                result_df = result_df.drop_duplicates(subset=['Task ID'])
                
                result_df = result_df.sort_values('Date (Pacific Time)')
                result_df['Date (Pacific Time)'] = result_df['Date (Pacific Time)'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Display result
                st.subheader(f"RaterHub Tasks for {selected_month} {selected_year}")
                st.dataframe(result_df, use_container_width=True)
                
                # Download button for the results
                csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name=f"raterhub_tasks_{selected_month}_{selected_year}.csv",
                    mime="text/csv"
                )
                
                # Display statistics
                st.subheader("Statistics")
                total_tasks = len(result_df)
                st.write(f"Total unique RaterHub tasks: {total_tasks}")
                total_visits = len(raterhub_df.dropna(subset=['task_id']))
                st.write(f"Total RaterHub visits (including duplicates): {total_visits}")
                
                if total_visits > total_tasks:
                    st.write(f"Removed {total_visits - total_tasks} duplicate task entries")
                
                if total_tasks > 0:
                    # Group by date and count tasks per day
                    result_df['Date Only'] = pd.to_datetime(result_df['Date (Pacific Time)']).dt.date
                    tasks_by_day = result_df.groupby('Date Only').size().reset_index(name='Count')
                    tasks_by_day.columns = ['Date', 'Number of Tasks']
                    
                    # Display tasks by day
                    st.subheader("Tasks by Day")
                    st.bar_chart(tasks_by_day.set_index('Date'))
                    st.dataframe(tasks_by_day)
                
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.error("Please make sure your file has the correct format with columns: order, id, date, time, title, url")
        st.error("If you're having issues with the CSV format, try checking that the date and time columns are properly formatted.")

# Add information about the app
st.sidebar.header("About")
st.sidebar.info(
    "This app processes browser history data to extract RaterHub tasks. "
    "Upload an Excel file containing your browser history and select the month "
    "to analyze. The app will identify RaterHub URLs and extract the task IDs."
)

st.sidebar.header("Instructions")
st.sidebar.markdown(
    """
    1. Select the month and year to analyze
    2. Upload your browser history CSV file (.csv)
    3. The file should contain the following columns:
       - order
       - id
       - date
       - time
       - title
       - url
    4. View the results and download as CSV if needed
    """
)