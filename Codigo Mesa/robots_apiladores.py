from random import randint
from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.visualization.modules import CanvasGrid, TextElement
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter

from pathfinding.core.grid import Grid as Path_grid
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.finder.a_star import AStarFinder
import numpy


class TotalSteps(TextElement):
    """
    Display a text count of how many happy agents = 0 xd.
    """

    def __init__(self):
        pass

    def render(self, model):
        return "Pasos en total: " + str(model.schedule.steps* model.agentsN) + "\n"

class Robot(Agent):
    def __init__(self, model, pos, C, R):
        super().__init__(model.next_id(), model)
        self.pos = pos
        self.matrix = numpy.ones((C,R), dtype=int)
        self.limit = C
        self.hasBox = False
        self.currentBox = Box(self.model, (0,0))
        self.x = randint(0, self.limit - 1)

    def findShortestPath(self, moves):
        for position in moves:
            agentsList = self.model.grid.get_cell_list_contents(position)
            for agent in agentsList:
                if self.model.count_boxes_on_cord(agentsList) < 5:
                    if(type(agent) == Box and agent.active):
                        if(self.hasBox):
                            return position
                        else:
                            if(self.model.count_boxes_on_cord(agentsList) < 2):
                                return position
        
        return self.random.choice(moves)
    
    def step(self):
        agentsList = self.model.grid.get_cell_list_contents(self.pos)
        next_moves = self.model.grid.get_neighborhood(self.pos, moore=True, radius = 10)
        closestTile = self.findShortestPath(next_moves)
        grid = Path_grid(matrix=self.matrix)
        startP = grid.node(self.pos[0], self.pos[1])
        endP = grid.node(closestTile[0], closestTile[1])
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        next_move, runs = finder.find_path(startP, endP, grid)
        for agent in agentsList:
            if(type(agent) == Box and agent.active):
                if(self.hasBox and self.model.count_boxes_on_cord(agentsList) < 5 ):
                    self.hasBox = False
                    self.model.grid.move_agent(self.currentBox, self.pos)
                else:
                    if(self.model.count_boxes_on_cord(agentsList) == 1 and (not agent.isStack)):
                        agent.active = False
                        self.currentBox = agent
                        self.hasBox = True
                        self.model.grid.move_agent(self, next_move[1])
                    else:
                        self.model.grid.move_agent(self, next_move[1])  
            else: 
                if(self.model.count_boxes(self.model) == 0 and (self.model.count_stacks(self.model) == 0 or (self.model.count_complete_stacks(self.model) > 0 and self.model.count_incomplete_stacks(self.model) == 0))):
                    if self.hasBox:
                        if(self.x == self.pos[0]):
                            self.hasBox = False
                            self.currentBox.active = True
                            self.currentBox.isStack = True
                            self.model.grid.move_agent(self.currentBox, self.pos)
                            self.model.grid.move_agent(self, next_move[1]) 
                        else:
                            grid = Path_grid(matrix=self.matrix)
                            startO = grid.node(self.pos[0], self.pos[1])
                            endO = grid.node(self.x, 0)
                            finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
                            next_move, runs = finder.find_path(startO, endO, grid)
                            self.model.grid.move_agent(self, next_move[1])
                else:
                    self.model.grid.move_agent(self, next_move[1])
        

class Box(Agent):
    def __init__(self, model, pos):
        super().__init__(model.next_id(), model)
        self.pos = pos
        self.active = True
        self.isStack = False

    def serialize(self):
        return {"id": self.unique_id,
                "x": self.pos[0],
                "y": self.pos[1],
                "active": self.active,
                "isStack": self.isStack}

class Stack(Agent):
    def __init__(self, model, pos, boxn):
        super().__init__(model.next_id(), model)
        self.pos = pos
        self.boxNumber = boxn

class Maze(Model):
    def __init__(self, C = 15, R = 15, boxNumber = 7, maxSteps = 500):
        super().__init__()
        self.schedule = RandomActivation(self)
        self.grid = MultiGrid(C, R, torus=False)
        self.maxSteps = maxSteps 
        self.agentsN = 5
        self.stacks = 0
        boxTiles = boxNumber
        self.robots = []

        matrix = numpy.zeros((C,R))

        while (boxTiles > 0):
            row = randint(0, R-1)
            column = randint(0, C-1)
            if(matrix[column][row] == 0):
                matrix[column][row] = 1
                boxTiles -= 1
 
        for n in range(self.agentsN):
            row = randint(0, R-1)
            column = randint(0, C-1)
            while(matrix[column][row] == 1):
                row = randint(0, R-1)
                column = randint(0, C-1)
            robot = Robot(self, (column, row), C, R)
            self.grid.place_agent(robot, robot.pos)
            self.schedule.add(robot)
            self.robots.append(robot)

        for _,x,y in self.grid.coord_iter():
            if matrix[y][x] == 1:
                box = Box(self, (x, y))
                self.grid.place_agent(box, box.pos)
                self.schedule.add(box)
    
    @staticmethod
    def updateStacks(model):
        for _,x,y in model.grid.coord_iter():
            agentsList = model.grid.get_cell_list_contents((x,y))
            count = model.count_boxes_on_cord(agentsList)
            stackExist = False
            if count > 1:
                for agent in agentsList:
                        if(type(agent) == Stack):
                            agent.boxNumber = count
                            stackExist = True
                        else: continue
                if(not stackExist):
                    stack = Stack(model, (x,y), count)
                    model.grid.place_agent(stack, stack.pos)
                    model.schedule.add(stack)

    @staticmethod
    def count_boxes(model):
        count = 0
        for agent in model.schedule.agents:
                if type(agent) == Box and agent.active:
                    count += 1
        return count - model.count_stacks(model)

    @staticmethod
    def count_stacks(model):
        count = 0
        for _,x,y in model.grid.coord_iter():
            agentsList = model.grid.get_cell_list_contents((x,y))
            if(model.count_boxes_on_cord(agentsList) > 1 or (model.count_boxes_on_cord(agentsList) == 1 and model.is_box_stack(agentsList))):
                count += 1
        return count

    @staticmethod
    def count_incomplete_stacks(model):
        count = 0
        for _,x,y in model.grid.coord_iter():
            agentsList = model.grid.get_cell_list_contents((x,y))
            if((model.count_boxes_on_cord(agentsList) > 1 and model.count_boxes_on_cord(agentsList) < 5) or (model.count_boxes_on_cord(agentsList) == 1 and model.is_box_stack(agentsList))):
                count += 1
        return count

    @staticmethod
    def is_box_stack(list):
        for agent in list:
            if type(agent) == Box and agent.isStack:
                return True
        return False
    
    @staticmethod
    def count_complete_stacks(model):
        count = 0
        for _,x,y in model.grid.coord_iter():
            agentsList = model.grid.get_cell_list_contents((x,y))
            if(model.count_boxes_on_cord(agentsList) == 5):
                count += 1
        return count

    @staticmethod
    def count_boxes_on_cord(list):
        count = 0
        for agent in list:
            if type(agent) == Box:
                count += 1
        return count

    @staticmethod
    def robots_are_free(model):
        count = 0
        for agent in model.robots:
            if not agent.hasBox:
                count += 1
        if count == 5:
            return True
        return False

    def step(self):
        self.updateStacks(self)
        if(self.schedule.steps >= self.maxSteps or (self.count_boxes(self) == 0 and self.robots_are_free(self))):
            self.running = False
        else:
            self.schedule.step()

"""def agent_portrayal(agent):
    if(type(agent) == Robot):
        if(agent.hasBox):
            return {"Shape": "robot-caja.png", "Layer": 2}
        else:
            return {"Shape": "robot-industrial.png", "Layer": 1}
    else:
        if agent.active:
            agentsList = agent.model.grid.get_cell_list_contents(agent.pos)
            count = agent.model.count_boxes_on_cord(agentsList)
            if(count == 1):
                return {"Shape": "rect", "w": 1, "h": 1, "Filled": "true", "Color": "#C5EFAC", "Layer": 0}
            if(count == 2):
                return {"Shape": "rect", "w": 1, "h": 1, "Filled": "true", "Color": "#ACBDEF", "Layer": 0}
            if(count == 3):
                return {"Shape": "rect", "w": 1, "h": 1, "Filled": "true", "Color": "#FFF192", "Layer": 0}
            if(count == 4):
                return {"Shape": "rect", "w": 1, "h": 1, "Filled": "true", "Color": "#FFD1B4", "Layer": 0}
            if(count == 5):
                return {"Shape": "rect", "w": 1, "h": 1, "Filled": "true", "Color": "#D0ACEF", "Layer": 0}
  

grid = CanvasGrid(agent_portrayal, 15, 15, 450, 450)

#chart = ChartModule([{"Label": "Percent clean", "Color": "Black"}], data_collector_name='datacollector')
text = TotalSteps()
server = ModularServer(Maze, 
                        [grid, text], 
                        "Robot Limpiador", 
                        { "boxNumber": UserSettableParameter("slider", "Numero de cajas", 7, 5, 200, 1),
                        "maxSteps": UserSettableParameter("slider", "Maximo numero de pasos", 500, 1, 500, 1)
        })
server.port = 8525
server.launch()"""