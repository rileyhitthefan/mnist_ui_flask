# Flask application for managing MNIST experiments

from flask import Flask, request, render_template_string, redirect, jsonify
from database import init_db, insert_experiment, get_all_experiments, get_running_jobs, job_exists
from mnist import run_experiment
import threading

# initialize Flask app and database
app = Flask(__name__)
init_db()

# HTML template can be defined in a separate file, combined for simplicity
template = """
<!DOCTYPE html>
<html>
    <head>
        <title>Experiment Management System</title>
    
        <style>
            /* style for progress bar */
            .job-row {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
            }
            .progress-bar-wrapper {
                flex: 1;
                background: #ddd;
                height: 20px;
                border-radius: 4px;
                overflow: hidden;
                margin-right: 10px;
            }
            .progress-bar-fill {
                height: 100%;
                background-color: #e4a8f0;
                transition: width 0.4s ease;
            }
            .job-text {
                white-space: nowrap;
                font-family: monospace;
                font-size: 14px;
            }
            
            /* style for table */
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 6px 12px;
                text-align: center;
            }
            th a {
                text-decoration: none;
                color: black;
                font-weight: bold;
            }
            
            /* style for user input form */
            form {
                margin: 20px 0;
                padding: 15px;
                border-radius: 4px;
            }
            form label {
                margin-right: 10px;
            }
            form input {
                margin-right: 20px;
                padding: 5px;
            }
            form button {
                padding: 5px 15px;
                cursor: pointer;
            }
        </style>

        <script>
            // assign sorting directions for experiments table
            let sortKey = "accuracy";
            let sortDirection = "desc";

            function setSort(key) {
                // toggle sort asc and desc when clicked
                if (sortKey === key) {
                    sortDirection = sortDirection === "asc" ? "desc" : "asc";
                } else {
                    sortKey = key;
                    sortDirection = "asc";
                }
                fetchExperiments();
            }

            // fetch and update experiments table
            async function fetchExperiments() {
                const res = await fetch(`/api/experiments?sort=${sortKey}&direction=${sortDirection}`);
                const data = await res.json();
                const tbody = document.getElementById("experimentsBody");
                tbody.innerHTML = "";
                
                data.forEach(exp => {
                    const row = `<tr>
                        <td>${exp.id}</td>
                        <td>${exp.lr}</td>
                        <td>${exp.epochs}</td>
                        <td>${exp.batch_size}</td>
                        <td>${(exp.accuracy || 0).toFixed(4)}</td>
                        <td>${(exp.runtime || 0).toFixed(2)}</td>
                        <td>${exp.status}</td>
                    </tr>`;
                    tbody.innerHTML += row;
                });
            }

            // fetch and update running jobs with progress bars
            async function fetchRunningJobs() {
                const res = await fetch(`/api/running_jobs`);
                const jobs = await res.json();
                const container = document.getElementById("runningJobsContainer");
                container.innerHTML = "";

                if (jobs.length === 0) {
                    container.innerHTML = "<p>No running jobs</p>";
                    return;
                }

                jobs.forEach(job => {
                    const progress = job.epochs > 0 ? (job.current_epoch / job.epochs) * 100 : 0;
                    const bar = 
                        `<div class="job-row">
                            <div class="progress-bar-wrapper">
                                <div class="progress-bar-fill" style="width:${progress}%;"></div>
                            </div>
                            <div class="job-text">
                                ID ${job.id} | Epoch ${job.current_epoch}/${job.epochs} | Loss: ${job.loss.toFixed(4)}
                            </div>
                        </div>`;
                    container.innerHTML += bar;
                });
            }

            // auto refresh 3 seconds
            setInterval(() => {
                fetchExperiments();
                fetchRunningJobs();
            }, 3000);

            // initial load
            window.onload = () => {
                fetchExperiments();
                fetchRunningJobs();
            };
            
            // reset confirmation
            async function resetDatabase() {
                const confirmed = confirm("Are you sure you want to reset all experiments?");
                if (confirmed) {
                    await fetch("/reset", { method: "POST" });
                    fetchExperiments();
                    fetchRunningJobs();
                    alert("Database has been reset.");
                }
            }
        </script>
    </head>
    
    <body>
        <h1>MNIST Experiment Manager</h1>

        <!-- form for experiment configuration -->
        <form method="POST">
            <label>Learning Rate:</label>
                <input type="number" step="0.0001" name="lr" value="0.001" required>
            <label>Epochs:</label>
                <input type="number" name="epochs" value="10" required>
            <label>Batch size:</label>
                <input type="number" name="batch_size" value="100" required>
            <button type="submit">Run</button>
            <button type="button" onclick="resetDatabase()">Reset All</button>
        </form>

        <!-- display running jobs -->
        <h2>Running Jobs</h2>
        <div id="runningJobsContainer">
            <!-- progress bars and job information -->
        </div>

        <!-- result table -->
        <h2>Experiments</h2>
        <table border="1">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Learning Rate</th>
                    <th>Epochs</th>
                    <th>Batch</th>
                    <th><a href="#" onclick="setSort('accuracy')">Accuracy ⇅</a></th>
                    <th><a href="#" onclick="setSort('runtime')">Runtime (secs) ⇅</a></th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="experimentsBody"></tbody>
        </table>
    </body>
</html>
"""

# route handlers
@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main route handler for the application.
    GET: renders the main page
    POST: handles new experiment submission
    """
    if request.method == "POST":
        # get experiment parameters
        lr = float(request.form["lr"])
        epochs = int(request.form["epochs"])
        batch_size = int(request.form["batch_size"])
        
        # only create new experiment if identical one doesn't exist
        if not job_exists(lr, epochs, batch_size):
            job_id = insert_experiment(lr, epochs, batch_size)
            # start experiment in background thread
            threading.Thread(
                target=run_experiment,
                args=(job_id, lr, epochs, batch_size),
                daemon=True
            ).start()
        return redirect("/")
    return render_template_string(template)

@app.route("/api/experiments")
def api_experiments():
    """API endpoint to get sorted experiment results"""
    sort_key = request.args.get("sort", "accuracy")
    direction = request.args.get("direction", "desc")
    return jsonify(get_all_experiments(sort_key, direction))

@app.route("/api/running_jobs")
def api_running_jobs():
    """API endpoint to get currently running experiments"""
    return jsonify(get_running_jobs())

@app.route("/reset", methods=["POST"])
def reset_db():
    """Handler to reset the database by deleting all experiments"""
    import sqlite3
    with sqlite3.connect("experiments.db") as conn:
        conn.execute("DELETE FROM experiments")
        conn.commit()
    return "", 204  # No content

if __name__ == "__main__":
    app.run(debug=True)
