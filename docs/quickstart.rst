Quickstart
===========

As we know, *modpoll* is a tool for communicating with Modbus devices, so ideally it makes more sense if you have a real modbus device on hand for the following test, but it is OK if you don't, we have deployed a virtual Modbus TCP device on cloud at `<modsim.topmaker.net:502>`_, the code is available in my another project `modsim<https://github.com/gavinying/modsim>`_, let's start expoloring *modpoll* tool with the virtual device *modsim*.

Test with modsim
------------------------
  *modsim* is a very simple Modbus TCP device simulator deployed on cloud, it populates the first 100 registers for each type of Coil / Discrete input / Input register / Holding register, 

  .. csv-table:: a title
   :header: "Object type","Access","Size","Address Space"
   :widths: 30, 20, 10, 30

   "Coil", "Read-write", "1 bit", "1-100"
   "Discrete Input", "Read-only", "1 bit", "10001-10100"
   "Input Register", "Read-only", "16 bits", "30001-30100"
   "Holding Register", "Read-write", "16 bits", "40001-40100"

  Using *modpoll* tool, we can poll the first 5 holding registers via the following command, 

  .. code-block:: shell

    modpoll --tcp modsim.topmaker.net --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv

  or run *modpoll* in docker,

  .. code-block:: shell

    docker run helloysd/modpoll --tcp modsim.topmaker.net --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv


  Meanwhile, if you prefer a local test or simply failed to connect to online *modsim* service, you can always launch your own device simulator locally via the following command, 

  .. code-block:: shell

    docker run -p 5020:5020 helloysd/modsim

  It will simulate a Modbus TCP device running at `<localhost:5020>`_, and you shall be able to connect it via the following command, 

  .. code-block:: shell

    modpoll --tcp localhost --tcp-port 5020 --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
