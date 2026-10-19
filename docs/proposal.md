# Project Proposal

## Title
AI-Powered University and Course Recommendation System for Students in Uganda (UniGuide Uganda)

## Problem statement
Thousands of Ugandan students complete UACE each year with limited access to accurate, up-to-date information about
university programmes, entry requirements, cut-off points, fees and career prospects. Information is scattered across
university websites and changes every academic year, making it difficult for students — especially those outside
Kampala — to choose courses they genuinely qualify for.

## Objectives
1. Help students identify courses and universities they are eligible for, based on their grades and preferences.
2. Provide A-Level subject-combination guidance linked to careers.
3. Match students against verified 2026/27 cut-off points and entry requirements.
4. Enable comparison of universities by location, fees, entry requirements and sponsorship options.
5. Guide students towards careers that match their programme.
6. Support international students through NCHE-compliant qualification handling.
7. Allow administrators to keep admission information up to date each academic year.

## Scope
- Web application (Flask + SQLite) running locally, deployable to any Python host.
- Student accounts, admin dashboard, recommendation engine, chatbot, comparison, PDF reports.
- Dataset of 10 universities / 31 programmes / 21 career paths with official sources, expandable.

## Description of the AI
The system uses a transparent rule-based engine (hard eligibility checks + weighted scoring) augmented by a
zero-parameter ranking layer that orders matches by status, suitability margin, budget fit and region fit. The
guidance chatbot resolves questions against the same verified dataset. No black-box models are used, which keeps
every recommendation explainable for an engineering project.

## Expected outcome
A reliable, mobile-friendly tool that turns a student's academic results into a shortlist of suitable programmes,
with reasons, entry requirements, fees and official application links.

## Stakeholders
Students (Ugandan and international), guardians, career guidance counsellors, and university admissions staff.