import matplotlib.pyplot as plt

def plot_bar(df, column):
    plt.figure()
    df[column].value_counts().plot(kind='bar')
    plt.savefig("static/images/chart.png")
    return "static/images/chart.png"