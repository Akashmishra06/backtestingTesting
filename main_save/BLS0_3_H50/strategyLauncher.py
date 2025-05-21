from configparser import ConfigParser
from logicLevelExecute import algoLogic
from strategyTools.statusUpdater import statusManager


if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')

    algoName = config.get('inputParameters', 'algoName')
    algoLogicObj = algoLogic()

    statusManager(algoName, {}, algoLogicObj, ['Process1'])