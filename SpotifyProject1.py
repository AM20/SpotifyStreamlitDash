import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.graph_objects as go

# Spotify API setup
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="7bc98e398d8e4718bff429eec9a86c2c",
                                               client_secret="095d77a7d203408c8aefe3cfdccc90b3",
                                               redirect_uri="http://localhost:8888/callback",
                                               scope="user-library-read",
                                               cache_path=".spotify_cache"))

# Function to search for songs by name
def search_songs(query):
    results = sp.search(q=query, type='track', limit=10)
    tracks = []
    for item in results['tracks']['items']:
        audio_features = sp.audio_features(item['id'])[0]
        tracks.append({
            'name': item['name'],
            'artist': item['artists'][0]['name'],
            'danceability': audio_features['danceability'],
            'energy': audio_features['energy'],
            'valence': audio_features['valence'],
            'tempo': audio_features['tempo'],
            'id': item['id'],
            'uri': item['uri']
        })
    return pd.DataFrame(tracks)

# Function to find similar songs based on audio features
def find_similar_songs(song_id):
    recommendations = sp.recommendations(seed_tracks=[song_id], limit=5)
    similar_tracks = []
    for item in recommendations['tracks']:
        audio_features = sp.audio_features(item['id'])[0]
        similar_tracks.append({
            'name': item['name'],
            'artist': item['artists'][0]['name'],
            'danceability': audio_features['danceability'],
            'energy': audio_features['energy'],
            'valence': audio_features['valence'],
            'tempo': audio_features['tempo'],
            'uri': item['uri']
        })
    return pd.DataFrame(similar_tracks)

# Streamlit layout
st.title("Spotify Audio Feature Analysis Dashboard")
st.write("Search for a track and get audio feature analysis along with similar song recommendations.")

# Input field for song search
song_query = st.text_input("Search for a song", key="song_search")
search_results = pd.DataFrame()

# Search for songs based on query
if song_query:
    search_results = search_songs(song_query)

# Display search results for selection
if not search_results.empty:
    selected_song = st.selectbox('Select a song from the list', search_results['name'].unique(), key="select_song")

    if selected_song:
        # Get the selected song's data (a single row)
        selected_song_row = search_results[search_results['name'] == selected_song]  # Keep as DataFrame

        # Get the song ID for recommendations
        song_id = selected_song_row.iloc[0]['id']

        # Create radar chart for audio feature analysis
        def create_radar_chart(row):
            categories = ['danceability', 'energy', 'valence', 'tempo']
            fig = go.Figure()

            fig.add_trace(go.Scatterpolar(
                r=[row['danceability'].values[0], row['energy'].values[0], row['valence'].values[0], row['tempo'].values[0]],
                theta=categories,
                fill='toself',
                name=row['name'].values[0]
            ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1]),
                ),
                showlegend=True
            )
            return fig

        # Display radar chart for the selected song
        radar_chart = create_radar_chart(selected_song_row)
        st.plotly_chart(radar_chart)

        # Display Spotify Play Button for the selected song
        def create_spotify_button(track_uri):
            return f"""
            <iframe src="https://open.spotify.com/embed/track/{track_uri.split(':')[-1]}"
            width="300" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>
            """

        st.write(f"Listen to {selected_song}:")
        st.markdown(create_spotify_button(selected_song_row.iloc[0]['uri']), unsafe_allow_html=True)

        # Recommend similar songs
        st.write("Similar Songs:")
        similar_songs_df = find_similar_songs(song_id)

        for idx, row in similar_songs_df.iterrows():
            st.write(f"{row['name']} by {row['artist']}")
            st.markdown(create_spotify_button(row['uri']), unsafe_allow_html=True)

        # Emotional comparison radar chart
        def create_emotional_comparison_radar_chart(selected_song_row, similar_songs_df):
            categories = ['valence', 'energy', 'danceability', 'tempo']
            
            # Create the figure
            fig = go.Figure()
            
            # Add the selected song's radar trace
            fig.add_trace(go.Scatterpolar(
                r=[selected_song_row['valence'].values[0], selected_song_row['energy'].values[0], selected_song_row['danceability'].values[0], selected_song_row['tempo'].values[0]],
                theta=categories,
                fill='toself',
                name=f"Selected: {selected_song_row['name'].values[0]}"
            ))
            
            # Add similar songs' radar traces
            for i, row in similar_songs_df.iterrows():
                fig.add_trace(go.Scatterpolar(
                    r=[row['valence'], row['energy'], row['danceability'], row['tempo']],
                    theta=categories,
                    fill='toself',
                    name=f"Recommended: {row['name']}"
                ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1]),
                ),
                showlegend=True,
                title="Emotional Profile Comparison"
            )

            return fig

        # Plot emotional comparison radar chart
        emotion_comparison_chart = create_emotional_comparison_radar_chart(selected_song_row, similar_songs_df)
        st.plotly_chart(emotion_comparison_chart)

        # Audio feature comparison table
        def create_audio_feature_comparison_table(selected_song_row, similar_songs_df):
            # Add the selected song as the first row
            comparison_df = pd.concat([selected_song_row, similar_songs_df], ignore_index=True)
            
            # Display relevant audio features
            comparison_df = comparison_df[['name', 'artist', 'danceability', 'energy', 'valence', 'tempo']]
            comparison_df.columns = ['Song', 'Artist', 'Danceability', 'Energy', 'Valence', 'Tempo']
            
            return comparison_df

        # Display comparison table
        st.write("Audio Feature Comparison Table")
        comparison_table = create_audio_feature_comparison_table(selected_song_row, similar_songs_df)
        st.dataframe(comparison_table)

        # Function to find opposite songs based on audio features
        def find_opposite_songs(selected_song_row):
            # Define opposite by inversing the audio features of the selected song
            selected_features = selected_song_row.iloc[0][['danceability', 'energy', 'valence', 'tempo']].values
            opposite_songs = []
    
            # Fetch recommendations from Spotify based on inverted features
            recommendations = sp.recommendations(seed_tracks=[selected_song_row.iloc[0]['id']], limit=50)  # Fetch a larger pool

            for item in recommendations['tracks']:
                audio_features = sp.audio_features(item['id'])[0]
                # Calculate "opposite" score (difference from inverted features)
                opposite_score = abs(1 - audio_features['danceability'] - selected_features[0]) + \
                                 abs(1 - audio_features['energy'] - selected_features[1]) + \
                                 abs(1 - audio_features['valence'] - selected_features[2]) + \
                                 abs(1 - audio_features['tempo']/200 - selected_features[3]/200)
                
                opposite_songs.append({
                    'name': item['name'],
                    'artist': item['artists'][0]['name'],
                    'danceability': audio_features['danceability'],
                    'energy': audio_features['energy'],
                    'valence': audio_features['valence'],
                    'tempo': audio_features['tempo'],
                    'opposite_score': opposite_score,
                    'uri': item['uri']
                })
            
            # Sort songs by highest opposite score and return top 3
            opposite_songs_df = pd.DataFrame(opposite_songs).sort_values(by='opposite_score', ascending=False).head(3)
            return opposite_songs_df

        # Add opposite songs section
        st.write("Songs Most Opposite to the Selected Song:")
        opposite_songs_df = find_opposite_songs(selected_song_row)

        for idx, row in opposite_songs_df.iterrows():
            st.write(f"{row['name']} by {row['artist']}")
            st.markdown(create_spotify_button(row['uri']), unsafe_allow_html=True)

        # Radar chart comparison for opposite songs
        def create_opposite_radar_chart(selected_song_row, opposite_songs_df):
            categories = ['danceability', 'energy', 'valence', 'tempo']
            
            # Create the figure
            fig = go.Figure()
            
            # Add the selected song's radar trace
            fig.add_trace(go.Scatterpolar(
                r=[selected_song_row.iloc[0]['danceability'], selected_song_row.iloc[0]['energy'], selected_song_row.iloc[0]['valence'], selected_song_row.iloc[0]['tempo']],
                theta=categories,
                fill='toself',
                name=f"Selected: {selected_song_row.iloc[0]['name']}"
            ))
            
            # Add opposite songs' radar traces
            for i, row in opposite_songs_df.iterrows():
                fig.add_trace(go.Scatterpolar(
                    r=[row['danceability'], row['energy'], row['valence'], row['tempo']],
                    theta=categories,
                    fill='toself',
                    name=f"Opposite: {row['name']}"
                ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1]),
                ),
                showlegend=True,
                title="Opposite Songs Audio Feature Comparison"
            )

            return fig

        # Plot opposite songs radar chart
        opposite_radar_chart = create_opposite_radar_chart(selected_song_row, opposite_songs_df)
        st.plotly_chart(opposite_radar_chart)
