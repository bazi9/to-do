# Modern Flask ToDo Application

A fully responsive, feature-rich Task Management application built with Python (Flask) and SQLite. Designed with a clean, modern UI using Bootstrap 4.

## Features
* **Hierarchical Task Management:** Create Main Tasks, Subcategories, and dynamic Keywords.
* **Cascading Completions:** Completing all keywords automatically marks a subtask as done. Completing all subtasks automatically finishes the main project.
* **Smart UI Memory:** Your browser remembers which task tabs you left open/closed using `localStorage`.
* **Mobile-Optimized:** Fully responsive layouts that adapt beautifully to phones and tablets.
* **Role-Based Access Control (RBAC):** Built-in User and Admin roles.
* **Admin Dashboard:** Admins can view all users, track their completion stats, and promote/demote or delete accounts.
* **Root Account Protection:** The master owner account (`baziboo`) cannot be demoted or deleted.

## Technologies Used
* **Backend:** Python, Flask, Werkzeug (Security/Hashing), SQLite3
* **Frontend:** HTML5, CSS3, JavaScript (Vanilla/jQuery), Bootstrap 4, FontAwesome

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/bazi9/to-do.git](https://github.com/bazi9/to-do.git)
   cd to-do