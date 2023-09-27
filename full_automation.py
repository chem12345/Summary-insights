import pandas as pd
import time
from statistics import mean, median, stdev, variance
import scipy.stats as stats
from statsmodels.tsa.seasonal import seasonal_decompose
import json
import pyodbc

server = 'TECH-99'
database = 'chem_prod_copy'
username = 'sa'
password = '123456'

connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"

conn = pyodbc.connect(connection_string)
cursor = conn.cursor()
print(cursor)


# Function to call the API (dummy function for illustration)
def call_api_and_generate_summary(product, country):
    # async def generate_summary(product:int,country:str = None,year: int = None):
    query1 = 'SELECT * FROM SA_ChemPriceWeeklyNew'
    week = pd.read_sql(query1, conn)
    query2 = ' SELECT * FROM SA_CommentaryPricing'
    market = pd.read_sql(query2, conn)
    # Your API call and summary generation logic here
    # week=pd.read_excel('weekly_data.xlsx')
    # week=week.loc[week['Range']=='Weekly']
    week1 = week.loc[(week['Product'] == product) & (week['Country'] == country)]
    week1 = week1.rename({'ProductVariant': 'ProductVarient'}, axis=1)
    market1 = market.loc[market['Product'] == product]
    product_df = pd.merge(market1, week1, on=['ProductVarient'], how='inner')
    product_df['Date'] = pd.to_datetime(product_df['Date'], errors='coerce')
    newest = product_df.sort_values('Date', ascending=False)
    product_df = newest.loc[newest['year_x'] == '2023']
    # product_df = product_df.sort_values(by='Date', ascending=False)\
    try:
        product_name = product_df['ProductVarient'].iloc[0]
        # Calculate statistical values
        average_price = int(mean(product_df['count']))
        median_price = int(median(product_df['count']))
        highest_price = int(max(product_df['count']))
        lowest_price = int(min(product_df['count']))
        std_dev = int(stdev(product_df['count']))
        var = int(variance(product_df['count']))
        skewness = int(stats.skew(product_df['count']))
        kurtosis = int(stats.kurtosis(product_df['count']))

        # product_df['Moving_Avg'] = product_df['count'].rolling(window=7).mean()

        # Time series decomposition for trend and seasonality
        # Assuming df is indexed by date
        decomposed = seasonal_decompose(product_df['count'], period=7)
        trend_percentage = int(
            (decomposed.trend.dropna().iloc[-1] - decomposed.trend.dropna().iloc[0]) / decomposed.trend.dropna().iloc[
                0] * 100)
        seasonality_percentage = int(decomposed.seasonal.dropna().max() * 100)

        # Get the latest market situation, demand, supply, and plant shutdown info
        latest_market_situation = product_df['MarketSituation'].iloc[0]
        latest_demand = product_df['Demand'].iloc[0]
        latest_supply = product_df['Supply'].iloc[0]
        latest_plant_shutdown = product_df['PlantShutdown'].iloc[0]
        # week_number=week_number_to_month_and_week(product_df['Week'].iloc[0])[1]
        # month = week_number_to_month_and_week(product_df['Week'].iloc[0])[0]
        newest['month'] = newest['Date'].dt.month_name(locale='English')
        # newest['month'] = newest['Date'].dt.month
        month = newest['month'].iloc[0]
        # Generate the HTML summary using f-strings

        df = product_df[['Date', 'count', 'Min', 'Max']].drop_duplicates()
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%B-%Y')

        # Sort the DataFrame by date in descending order
        df = df.sort_values(by='Date', ascending=False)

        # Find the latest maximum price and its corresponding date
        latest_max = df.iloc[0]

        # Find the index of the latest maximum price in the sorted DataFrame
        latest_max_index = df.index[0]

        # Find the previous occurrences of this maximum price in different months
        previous_max_occurrences = df[
            (df['Max'] == latest_max['Max']) & (df['Date'].dt.month != latest_max['Date'].month)]

        # Calculate the time difference in months
        latest_date = latest_max['Date']
        previous_dates = previous_max_occurrences['Date']
        months_difference = (latest_date - previous_dates).dt.days // 30

        html_summary = f"""<!DOCTYPE html>
        <html>
        <head>
            <title>Product Price Analysis and Summary</title>
        </head>
        <body>

        <h1>Product Price Analysis and Summary</h1>

        <h2>Price Analysis:</h2>

        <ul>
            <li>Average Price: The average price of {product_name} during the month of {month} was approximately USD {average_price}</li>
            <li>Median Price: The median price , representing the middle value of {product_name} during {month}, was USD {median_price}.</li>
            <li>Highest Price: {product_name} reached its highest price at USD {highest_price} during the month of {month}. It took approximately {months_difference.min()} months to reach this peak price again.</li>
            <li>Lowest Price: {product_name} recorded its lowest price at USD {lowest_price} during the month of {month}. It took approximately 4 months to reach this low price again.</li>
        </ul>

        <h2>Statistical Insights:</h2>
        <ul>
            <li>Standard Deviation: The standard deviation in the price was USD {std_dev}. A higher standard deviation suggests greater price volatility, which could impact strategic planning and risk management.</li>
            <li>Skewness: {skewness}, indicating a symmetric price distribution. A positive or negative skewness might suggest a bias in price trends that requires attention.</li>
            <li>Kurtosis: The kurtosis value was {kurtosis}, indicating a normally distributed price. A higher kurtosis could imply more extreme price fluctuations, influencing long-term pricing strategies.</li>
        </ul>


        <h2>Market Situation:</h2>
        <ul>
            <li>Latest Information: {latest_market_situation}</li>
        </ul>

        <h2>Demand:</h2>
        <ul>
            <li>Latest Information: {latest_demand}</li>
        </ul>

        <h2>Supply:</h2>
        <ul>
            <li>Latest Information: {latest_supply}</li>
        </ul>

        <h2>Plant Shutdowns:</h2>
        <ul>
            <li>Latest Information: {latest_plant_shutdown}</li>
        </ul>
        <h2>Trend and Seasonality:</h2>
        <ul>
            <li>Trend Percentage: {trend_percentage}%</li>
            <li>Seasonality Percentage: {seasonality_percentage}%</li>
        </ul>
        </body>
        </html>"""

        # Return the HTML summary
        return {"html_summary": html_summary}
    except:
        string = 'Please mention Product Variant'
        return string


last_processed_log_id = 0
df_logs = pd.DataFrame(columns=['LogID', 'Product', 'InsertedDateTime', 'Country', 'Status'])

while True:
    new_logs_list = []

    query = f"SELECT * FROM tracking WHERE LogID > {last_processed_log_id} ORDER BY LogID"
    cursor.execute(query)
    logs = cursor.fetchall()

    for log in logs:
        # Check if this LogID is already processed and marked as 'Done' in the database
        cursor.execute(f"SELECT Status FROM tracking WHERE LogID = {log[0]}")
        db_status = cursor.fetchone()[0]

        if db_status == 'Done':
            print(f"Skipping LogID {log[0]} as it is already done.")
            continue

        # Process the log data here (print, store, or any other operation)
        print(log)
        last_processed_log_id = log[0]  # Assuming LogID is the first column

        # Call API and generate summary
        print(log[1])
        summary = call_api_and_generate_summary(log[1], log[10])

        print(summary)
        if summary:
            # Convert the summary dictionary to a JSON string
            summary_json = json.dumps(summary)

            cursor.execute(f"UPDATE tracking SET Status = 'Done', Summary = ? WHERE LogID = ?", (summary_json, log[0]))
            # Commit the transaction to save changes
            conn.commit()
        else:
            print(f"Summary is None for LogID {log[0]}")

        # Update the status in the database
        if summary:
            cursor.execute(f"UPDATE tracking SET Status = 'Done' WHERE LogID = {log[0]}")
            # Commit the transaction to save changes
            conn.commit()

        log_dict = {
            'LogID': log[0],
            'Product': log[1],
            # 'ProductVariant': log[2],
            'InsertedDateTime': log[-1],
            'Country': log[10],
            'Status': 'Done' if summary else 'Pending'
        }
        new_logs_list.append(log_dict)

    # Append new logs to the DataFrame only if there are new logs
    if new_logs_list:
        df_new_logs = pd.DataFrame(new_logs_list)
        df_logs = pd.concat([df_logs, df_new_logs], ignore_index=True)

    # Sleep for a defined interval (e.g., 10 seconds) before checking again
    time.sleep(10)
