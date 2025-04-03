from flask import Flask, render_template, request, send_from_directory, jsonify
import pandas as pd
import plotly.express as px
import plotly.utils
import json
import os
import plotly.graph_objects as go
import requests
import os
from sklearn.neighbors import NearestNeighbors
import folium
from folium.plugins import MarkerCluster
import bcrypt
from flask import Flask, render_template, request, jsonify, session, redirect, url_for


USER_CSV = "data/users.csv"
SEARCH_CSV = "data/searches.csv"
EV_CARS_CSV = "data/EV_cars.csv"

os.makedirs("data", exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")



def load_data():
    file_path = os.path.join(os.path.dirname(__file__), "data", "EV_cars.csv")

    if not os.path.exists(file_path):
        print("❌ ERROR: EV_cars.csv file not found.")
        return pd.DataFrame()

    try:
        data = pd.read_csv(file_path, na_values=['NA'], encoding='utf-8', dtype=str)
        print("✅ EV Data Loaded Successfully!")

        print(f"📊 DEBUG: Available columns in dataset: {list(data.columns)}")

        if "Brand" not in data.columns:
            print("⚠️ WARNING: 'Brand' column missing! Creating it now...")
            data["Brand"] = data["Car_name"].apply(lambda x: x.split()[0] if isinstance(x, str) else "Unknown")

        numeric_columns = ['Price.DE.', 'Range', 'Efficiency', 'Fast_charge', 'Top_speed', 'acceleration..0.100.', 'Battery']
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
                data[col] = data[col].fillna(data[col].median())

        data.to_csv(file_path, index=False, encoding="utf-8")
        print(f"✅ Brand column added & Cleaned data saved to: {file_path}")

        return data
    except Exception as e:
        print(f"❌ ERROR LOADING CSV: {e}")
        return pd.DataFrame()

ev_data = load_data()



import numpy as np
from sklearn.neighbors import NearestNeighbors

def load_search_data():
    if os.path.exists(SEARCH_CSV):
        df = pd.read_csv(SEARCH_CSV)
        if df.empty:
            return None
        return df
    return None

def train_recommendation_model():
    search_data = load_search_data()
    if search_data is None:
        return None, None

    search_data["budget"] = pd.to_numeric(search_data["budget"], errors='coerce')
    search_data["range"] = pd.to_numeric(search_data["range"], errors='coerce')


    features = ["budget", "range"]
    search_data = search_data.dropna(subset=features) 


    model = NearestNeighbors(n_neighbors=3, metric="euclidean")
    model.fit(search_data[features])

    return model, search_data


model, search_data = train_recommendation_model()



@app.route('/recommend', methods=['POST'])
def recommend():
    global model, search_data, ev_data  

    if model is None or search_data is None:
        return jsonify({"error": "Not enough search data to generate recommendations."})

    try:
        data = request.json
        user_budget = int(data["budget"])
        user_range = int(data["range"])

        distances, indices = model.kneighbors(np.array([[user_budget, user_range]]))
        recommendations = search_data.iloc[indices[0]][["brand", "budget", "range"]].to_dict(orient="records")

        def get_real_brands(recommendations):
            updated_recommendations = []
            seen_brands = set()  
    
            for rec in recommendations:
                matching_ev = ev_data[
                    (ev_data["Range"] >= rec["range"] - 20) & (ev_data["Range"] <= rec["range"] + 20) &
                    (ev_data["Price.DE."] >= rec["budget"] - 5000) & (ev_data["Price.DE."] <= rec["budget"] + 5000)
                ]
                if not matching_ev.empty:
                    brand_name = matching_ev["Brand"].values[0]
                    if brand_name not in seen_brands:  
                        rec["brand"] = brand_name
                        seen_brands.add(brand_name)
                        updated_recommendations.append(rec)
                else:
                    rec["brand"] = "Unknown"
                    updated_recommendations.append(rec)

            return updated_recommendations


        recommendations = get_real_brands(recommendations)

        return jsonify({"recommendations": recommendations})

    except Exception as e:
        return jsonify({"error": str(e)})




@app.route('/finder', methods=['GET', 'POST'])
def finder():
    if request.method == 'POST':
        try:
            
            min_range = int(request.form.get('range_min', 300))
            max_price = int(request.form.get('price_max', 50000))

            print(f"🔍 DEBUG: Filtering EVs with Range >= {min_range} and Price <= {max_price}")

            ev_data_numeric = ev_data.copy()
            ev_data_numeric[['Range', 'Price.DE.']] = ev_data_numeric[['Range', 'Price.DE.']].apply(pd.to_numeric, errors='coerce')

            filtered_cars = ev_data_numeric[
                (ev_data_numeric['Range'] >= min_range) & (ev_data_numeric['Price.DE.'] <= max_price)
            ].to_dict(orient='records')

            print(f"✅ DEBUG: Found {len(filtered_cars)} matching cars.")

            return render_template('finder.html', cars=filtered_cars)

        except Exception as e:
            print(f"❌ ERROR in filtering EVs: {e}")
            return render_template('finder.html', cars=[], error="Error processing request.")

    
    return render_template('finder.html', cars=[])


@app.route('/popular-evs')
def popular_evs():
    if not os.path.exists(SEARCH_CSV):
        return jsonify({"popular_evs": []})

    search_data = pd.read_csv(SEARCH_CSV)
    
    if "brand" not in search_data.columns:
        return jsonify({"popular_evs": []})

    popular_evs = search_data["brand"].value_counts().reset_index()
    popular_evs.columns = ["brand", "count"]

    popular_evs = popular_evs.merge(ev_data[["Brand", "Car_name"]], left_on="brand", right_on="Brand", how="left").drop(columns=["Brand"])
    
    return jsonify({"popular_evs": popular_evs.to_dict(orient="records")})



LIKED_EV_CSV = "data/liked_ev.csv"
USER_CSV = "data/users.csv"
EV_CSV = "data/EV_cars.csv"


@app.route('/like-ev', methods=['POST'])
def like_ev():
    liked_ev_file = LIKED_EV_CSV

    try:
        car_name = request.form.get("car_name") or request.json.get("car_name")
        email = request.form.get("email") or request.json.get("email")

        if not car_name or not email:
            return jsonify({"error": "Missing car name or email"}), 400

        if os.path.exists(USER_CSV):
            user_data = pd.read_csv(USER_CSV)
            if email not in user_data["email"].values:
                return jsonify({"error": "User does not exist. Please register first."}), 403

        if not os.path.exists(liked_ev_file):
            pd.DataFrame(columns=["email", "car_name"]).to_csv(liked_ev_file, index=False)

        liked_df = pd.read_csv(liked_ev_file)

        if ((liked_df["email"] == email) & (liked_df["car_name"] == car_name)).any():
            return jsonify({"message": f"You already liked {car_name}!"})

        new_like = pd.DataFrame([[email, car_name]], columns=["email", "car_name"])
        liked_df = pd.concat([liked_df, new_like], ignore_index=True)

        liked_df.to_csv(liked_ev_file, index=False)

        return jsonify({"message": f"You liked {car_name}!", "success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/most-liked-evs')
def most_liked_evs():
    if not os.path.exists(LIKED_EV_CSV):
        return jsonify({"most_liked": []})

    liked_data = pd.read_csv(LIKED_EV_CSV)

    if "car_name" not in liked_data.columns:
        return jsonify({"most_liked": []})

    liked_counts = liked_data["car_name"].value_counts().reset_index()
    liked_counts.columns = ["car_name", "count"]

    if os.path.exists(EV_CSV):
        ev_data = pd.read_csv(EV_CSV)
        liked_counts = liked_counts.merge(
            ev_data[["Car_name", "Brand"]],
            left_on="car_name",
            right_on="Car_name",
            how="left"
        ).drop(columns=["Car_name"])
    else:
        liked_counts["Brand"] = "Unknown"

    liked_counts["Brand"] = liked_counts["Brand"].fillna("Unknown")

    return jsonify({"most_liked": liked_counts.to_dict(orient="records")})





@app.route('/analysis')
def analysis():
    if ev_data.empty:
        return "Error: EV Data not loaded properly."

    theme = request.args.get('theme', 'dark')

    if theme == "light":
        plotly_template = "plotly_white"
        bg_color = "rgba(255, 255, 255, 1)"
        font_color = "black"
        color_scale = "Viridis"
    else:
        plotly_template = "plotly_dark"
        bg_color = "rgba(0, 0, 0, 0)"
        font_color = "white"
        color_scale = "Viridis"

    fig_price_vs_range = px.scatter(
        ev_data,
        x="Range",
        y="Price.DE.",
        color="Price.DE.",
        hover_name="Car_name",
        title="Price vs Range",
        color_continuous_scale=color_scale,
        template=plotly_template
    )

   
    fig_price_vs_range.update_layout(
        legend=dict(
            title="Price (€)",  
            x=1,  
            y=1,  
            bgcolor="rgba(0,0,0,0.5)",
            font=dict(color=font_color)
        ),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font=dict(color=font_color)
    )

    fig_acceleration = go.Figure()
    fig_acceleration.add_trace(go.Scatter(
        x=ev_data["acceleration..0.100."],
        y=ev_data["Car_name"],
        mode='lines+markers',
        marker=dict(
            size=8,
            color=ev_data["acceleration..0.100."],
            colorscale=color_scale,
            showscale=True  
        ),
        name="0-100 km/h Time"  
    ))

    fig_acceleration.update_layout(
        title="EV Acceleration (0-100 km/h) - Line Scatter",
        xaxis_title="0-100 km/h Time (seconds)",
        yaxis_title="EV Model",
        legend=dict(
            title="Acceleration (sec)",  
            x=1,  
            y=1,  
            bgcolor="rgba(0,0,0,0.5)",
            font=dict(color=font_color)
        ),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font=dict(color=font_color)
    )

    graphs = {
        "price_vs_range": json.dumps(fig_price_vs_range, cls=plotly.utils.PlotlyJSONEncoder),
        "acceleration": json.dumps(fig_acceleration, cls=plotly.utils.PlotlyJSONEncoder),
    }

    return render_template("analysis.html", graphs=graphs)





@app.route('/graphs')
def graphs():
    if ev_data.empty:
        return "Error: EV Data not loaded properly."

    fig_price = px.histogram(ev_data, x="Price.DE.", nbins=20, title="Price Distribution (€)", template="plotly_dark")
    fig_price.update_traces(name="EV Price Distribution", showlegend=True)
    fig_price.update_layout(legend=dict(
        title="Price (€)",  
        x=1,  
        y=1,  
        bgcolor="rgba(0,0,0,0.5)",
        font=dict(color="white")
    ))


    fig_range = px.histogram(ev_data, x="Range", nbins=20, title="Range Distribution (km)", template="plotly_dark")
    fig_range.update_traces(name="EV Range Distribution", showlegend=True)
    fig_range.update_layout(legend=dict(
        title="Range (km)",  
        x=1,  
        y=1,  
        bgcolor="rgba(0,0,0,0.5)",
        font=dict(color="white")
    ))

    fig_efficiency = px.histogram(ev_data, x="Efficiency", nbins=20, title="Efficiency Distribution (km/kWh)", template="plotly_dark")
    fig_efficiency.update_traces(name="EV Efficiency Distribution", showlegend=True)
    fig_efficiency.update_layout(legend=dict(
        title="Efficiency (km/kWh)",  
        x=1,  
        y=1,  
        bgcolor="rgba(0,0,0,0.5)",
        font=dict(color="white")
    ))

    graphs = {
        "price_distribution": json.dumps(fig_price, cls=plotly.utils.PlotlyJSONEncoder),
        "range_distribution": json.dumps(fig_range, cls=plotly.utils.PlotlyJSONEncoder),
        "efficiency_distribution": json.dumps(fig_efficiency, cls=plotly.utils.PlotlyJSONEncoder),
    }

    return render_template("graphs.html", graphs=graphs)



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/validate-questionnaire', methods=['POST'])
def validate_questionnaire():
    try:
        data = request.json

        brand_preference = data.get('brand', 'any')
        budget = int(data.get('budget', 100000))
        min_range = int(data.get('range', 200))
        fast_charge = data.get('fast_charge', 'no')
        priority = data.get('priority', 'efficiency')

        ev_data_numeric = ev_data.copy()
        ev_data_numeric[['Range', 'Price.DE.', 'Fast_charge', 'acceleration..0.100.', 'Efficiency']] = ev_data_numeric[
            ['Range', 'Price.DE.', 'Fast_charge', 'acceleration..0.100.', 'Efficiency']
        ].apply(pd.to_numeric, errors='coerce')

        matching_cars = ev_data_numeric[
            (ev_data_numeric['Price.DE.'] <= budget) & (ev_data_numeric['Range'] >= min_range)
        ]

        if brand_preference != "any":
            matching_cars = matching_cars[matching_cars['Brand'].str.contains(brand_preference, case=False, na=False)]

        if fast_charge == 'yes':
            matching_cars = matching_cars[matching_cars['Fast_charge'] > 100]

        if matching_cars.empty:
            return jsonify({"valid": False, "message": "No EVs match your selected criteria. Try adjusting your filters."})

        return jsonify({"valid": True})

    except Exception as e:
        return jsonify({"valid": False, "message": f"Error processing request: {e}"})





@app.route('/questionnaire', methods=['GET', 'POST'])
def questionnaire():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            brand_preference = request.form.get('brand', '').strip()
            budget = request.form.get('budget')  
            range_km = request.form.get('range')  
            fast_charge = request.form.get('fast_charge')
            priority = request.form.get('priority')

            any_budget = request.form.get("any_budget", "off")  
            any_range = request.form.get("any_range", "off")  

            print(f"🔍 DEBUG: User Inputs - Brand: {brand_preference}, Budget: {budget}, Range: {range_km}, Fast Charge: {fast_charge}, Priority: {priority}, Any Budget: {any_budget}, Any Range: {any_range}")

            budget = int(budget) if budget and budget != "any" and budget.isdigit() else None
            range_km = int(range_km) if range_km and range_km != "any" and range_km.isdigit() else None

            budget = None if any_budget == "on" else budget
            range_km = None if any_range == "on" else range_km

           
            ev_data_numeric = ev_data.copy()
            ev_data_numeric[['Range', 'Price.DE.', 'Fast_charge', 'acceleration..0.100.', 'Efficiency']] = ev_data_numeric[
                ['Range', 'Price.DE.', 'Fast_charge', 'acceleration..0.100.', 'Efficiency']
            ].apply(pd.to_numeric, errors='coerce')

            
            matching_cars = ev_data_numeric

            if budget is not None:
                matching_cars = matching_cars[matching_cars['Price.DE.'] <= budget]
                print(f"✅ DEBUG: {len(matching_cars)} cars left after budget filter (≤ €{budget})")

            if range_km is not None:
                matching_cars = matching_cars[matching_cars['Range'] >= range_km]
                print(f"✅ DEBUG: {len(matching_cars)} cars left after range filter (≥ {range_km} km)")

            if brand_preference and brand_preference.lower() != "any":
                matching_cars = matching_cars[
                    matching_cars['Brand'].astype(str).str.contains(brand_preference, case=False, na=False)
                ]
                print(f"✅ DEBUG: {len(matching_cars)} cars left after brand filter ({brand_preference})")

            if fast_charge == 'yes':
                matching_cars = matching_cars[matching_cars['Fast_charge'] > 100]
                print(f"✅ DEBUG: {len(matching_cars)} cars left after fast charge filter.")

            sort_column = 'acceleration..0.100.' if priority == 'performance' else 'Efficiency'
            ascending = False if priority == 'performance' else True  
            matching_cars = matching_cars.sort_values(by=sort_column, ascending=ascending)

            print(f"✅ FINAL MATCHES: {len(matching_cars)} cars found.")

            search_entry = pd.DataFrame([{
                "email": email,
                "brand": brand_preference,
                "budget": budget if budget is not None else "any",
                "range": range_km if range_km is not None else "any",
                "fast_charge": fast_charge,
                "priority": priority
            }])

            if os.path.exists(SEARCH_CSV):
                existing_searches = pd.read_csv(SEARCH_CSV)
                updated_searches = pd.concat([existing_searches, search_entry], ignore_index=True)
            else:
                updated_searches = search_entry

            updated_searches.to_csv(SEARCH_CSV, index=False)

            if not matching_cars.empty:
                return render_template('questionnaire_results.html', cars=matching_cars.to_dict(orient='records'))

            print("❌ DEBUG: No matching EVs found.")
            return render_template('questionnaire_results.html', cars=[], error="❌ No EVs match your search criteria. Try adjusting the filters.")

        except Exception as e:
            print(f"❌ ERROR processing questionnaire: {e}")
            return render_template('questionnaire_results.html', cars=[], error=f"Error processing request: {e}")

    return render_template('questionnaire.html', cars=[])


@app.route('/database-view')
def database_view():
    if os.path.exists(USER_CSV):
        users_df = pd.read_csv(USER_CSV)
    else:
        users_df = pd.DataFrame(columns=["name", "email", "phone", "country"])

    if os.path.exists(SEARCH_CSV):
        search_df = pd.read_csv(SEARCH_CSV)
    else:
        search_df = pd.DataFrame(columns=["email", "brand", "budget", "range", "fast_charge", "priority"])

    if os.path.exists("data/liked_ev.csv"):
        liked_df = pd.read_csv("data/liked_ev.csv")
        
        liked_counts = liked_df["car_name"].value_counts().reset_index()
        liked_counts.columns = ["Car_name", "Likes"]
        liked_counts = liked_counts.sort_values(by="Likes", ascending=False)
    else:
        liked_counts = pd.DataFrame(columns=["Car_name", "Likes"])

    return render_template(
        'database_view.html',
        users=users_df.to_dict(orient='records'),
        searches=search_df.to_dict(orient='records'),
        liked_cars=liked_counts.to_dict(orient='records')  
    )



@app.route('/results', methods=['GET'])
def results():
    try:

        brand_preference = request.args.get('brand', 'any')
        budget = int(request.args.get('budget', 100000))
        range_km = int(request.args.get('range', 200))
        fast_charge = request.args.get('fast_charging', 'no')
        priority = request.args.get('efficiency_or_performance', 'efficiency')


        ev_data_numeric = ev_data.copy()
        ev_data_numeric[['Range', 'Price.DE.', 'Fast_charge', 'acceleration..0.100.', 'Efficiency']] = ev_data_numeric[[
            'Range', 'Price.DE.', 'Fast_charge', 'acceleration..0.100.', 'Efficiency'
        ]].apply(pd.to_numeric, errors='coerce')

        matching_cars = ev_data_numeric

        if budget is not None:
            matching_cars = matching_cars[matching_cars['Price.DE.'] <= budget]

        if range_km is not None:
            matching_cars = matching_cars[matching_cars['Range'] >= range_km]

        if brand_preference != 'any':
            matching_cars = matching_cars[matching_cars['Brand'].str.contains(brand_preference, case=False, na=False)]

        if fast_charge == 'yes':
            matching_cars = matching_cars[matching_cars['Fast_charge'] > 100]


        sort_column = 'acceleration..0.100.' if priority == 'performance' else 'Efficiency'
        matching_cars = matching_cars.sort_values(by=sort_column, ascending=(priority == 'efficiency'))

        print(f"✅ DEBUG: {len(matching_cars)} matching cars found.")  

        if not matching_cars.empty:
            print(f"✅ DEBUG: Cars to display: {matching_cars[['Car_name', 'Brand', 'Range', 'Price.DE.']].head()}") 
            return render_template('questionnaire_results.html', cars=matching_cars.to_dict(orient='records'))

        return render_template('questionnaire_results.html', cars=[], error="❌ No matching EVs found.")
    except Exception as e:
        print(f"❌ ERROR processing results: {e}")
        return render_template('questionnaire_results.html', cars=[], error=f"Error processing request: {e}")




@app.route("/questionnaire_results", methods=["GET"])
def questionnaire_results():
    try:
        search_df = pd.read_csv(SEARCH_CSV)
        search_df.fillna("", inplace=True)  

        liked_df = pd.read_csv(LIKED_EV_CSV)
        if not liked_df.empty:
            most_liked_evs = (
                liked_df.groupby("car_name")["email"]
                .count()
                .reset_index(name="Likes")
                .sort_values(by="Likes", ascending=False)
            )
        else:
            most_liked_evs = pd.DataFrame(columns=["car_name", "Likes"]) 

        most_liked_evs = most_liked_evs.to_dict(orient="records")

        return render_template(
            "questionnaire_results.html",
            most_liked_evs=most_liked_evs
        )

    except Exception as e:
        return f"❌ Error loading questionnaire results: {str(e)}"





import os
import pandas as pd
import bcrypt
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

DATA_FOLDER = "data"
USER_CSV = os.path.join(DATA_FOLDER, "users.csv")  

os.makedirs(DATA_FOLDER, exist_ok=True)  


app.secret_key = "123"  

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def ensure_user_csv():
    if not os.path.exists(USER_CSV):
        pd.DataFrame(columns=["name", "email", "password"]).to_csv(USER_CSV, index=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    ensure_user_csv()  

    if request.method == 'GET':
        return render_template('register.html')

    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400


    user_data = pd.read_csv(USER_CSV)

    if email in user_data["email"].values:
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = hash_password(password)

    new_user = pd.DataFrame([{"name": name, "email": email, "password": hashed_pw}])
    user_data = pd.concat([user_data, new_user], ignore_index=True)
    user_data.to_csv(USER_CSV, index=False)

    return jsonify({"message": "Registration successful!"}), 200



@app.route('/login', methods=['GET', 'POST'])
def login():
    ensure_user_csv()  

    if request.method == 'GET':
        return render_template('login.html')

    try:
        data = request.get_json(force=True)
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        user_data = pd.read_csv(USER_CSV)

        if email in user_data["email"].values:
            stored_password = user_data[user_data["email"] == email]["password"].values[0]

            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                session['user_email'] = email
                return jsonify({
                    "message": "✅ Login successful!",
                    "success": True,
                    "redirect": "/"
                }), 200
            else:
                return jsonify({"error": "❌ Invalid password"}), 401
        else:
            return jsonify({"error": "❌ User not found"}), 404

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500







@app.route("/map")
def charging_map():
    csv_path = "data/ev_charging_stations_ireland (1).csv"
    df = pd.read_csv(csv_path)

    m = folium.Map(location=[53.4, -7.9], zoom_start=7)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        popup_html = f"""
        <strong>{row['Address']}</strong><br>
        📍 {row['County']}<br>
        🔌 Chargers: {row['Nr. Chargers']}<br>
        ⚡ CCS: {row.get('CCS kWs', 'N/A')} kW<br>
        ⚡ CHAdeMO: {row.get('CHAdeMO kWs', 'N/A')} kW<br>
        ⚡ AC Fast: {row.get('AC Fast kWs', 'N/A')} kW<br>
        🕒 {row['Open Hours']}
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="green", icon="bolt", prefix="fa")
        ).add_to(marker_cluster)

    
    map_file = "static/charging_map.html"
    m.save(map_file)

    return render_template("charging_map.html")













@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login'))  




        
if __name__ == '__main__':
    app.run(debug=True)








