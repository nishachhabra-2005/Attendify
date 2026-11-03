
import streamlit as st
def subject_card(name, code, section, stats=None, footer_callback=None):
    html = f"""
        <div style="background:#151823; border-left: 8px solid #8B5CF6; padding:25px; border-radius: 20px; border: 1px solid #292D3A; margin-bottom:20px;">
        <h3 style="margin:0; color: #E5E7EB; font-size: 1.5rem ">{name}</h3>
        <p style="color:#9CA3AF; margin:10px 0;">Code : <span style="background:#252938; color:#A78BFA; padding:2px 8px; border-radius:5px;">{code} </span> | Section : {section}</p>
        
        """
    
    if stats:
        html+= """
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
        """
        for icon, label, value in stats:
            html+= f'<div style="background: #8B5CF620; color:#E5E7EB; padding:5px 12px; border-radius:12px; font-size:0.9rem">{icon} <b>{value}</b> {label} </div>'
        
        html+= "</div>"

    st.markdown(html, unsafe_allow_html=True)

    if footer_callback:
        footer_callback()
