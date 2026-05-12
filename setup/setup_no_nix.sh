cargo install joule-profiler-cli

if [ ! -d ../gson ]; then
    echo "Cloning gson project..."
    git clone https://github.com/google/gson.git ../gson
else
    echo "gson already exists, skipping clone."
fi

if [ ! -d ../maven ]; then
    echo "Installing Maven..."

    curl -O https://dlcdn.apache.org/maven/maven-3/3.9.15/binaries/apache-maven-3.9.15-bin.tar.gz
    tar -xzf apache-maven-3.9.15-bin.tar.gz
    rm apache-maven-3.9.15-bin.tar.gz
    mv apache-maven-3.9.15 ../maven

    echo "Maven installed."
else
    echo "Maven already exists, skipping installation."
fi

sudo cpupower frequency-set -g performance
echo off | sudo tee /sys/devices/system/cpu/smt/control
sudo sysctl kernel.perf_event_paranoid=0
