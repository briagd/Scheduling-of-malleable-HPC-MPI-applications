from dataclasses import dataclass
from random import seed
from statistics import mean, stdev

import structlog

from .Experiments import Experiments
from .Particle import Particle
from .Scheduler import SchedulerConfig


@dataclass
class EpochCost:
    """A container for the calculated costs of one epoch.
    """

    epoch: int  #: The epoch identifier.
    min: float  #: The minimum calculated cost during the epoch.
    max: float  #: The maximum calculated cost during the epoch.
    mean: float  #: The mean cost value of the epoch.
    std: float  #: The standard deviation of the calculated costs during the epoch.

    @classmethod
    def from_costs(cls, epoch: int, particles_cost: list):
        """Constructs an EpochCost object from a list of calculated costs.

        Args:
            epoch: The epoch identifier.
            particles_cost: A list of all the calculated costs during the epoch.

        Returns:
            EpochCost: An EpochCost object.
        """
        return cls(
            epoch,
            min(particles_cost),
            max(particles_cost),
            mean(particles_cost),
            stdev(particles_cost),
        )

    def to_dict(self):
        """Converts an EpochCost attributes into a python dictionary

        Returns:
            dict: A dictionary with the attributes of an EpochCost object.
        """

        dict_obj = self.__dict__
        return dict_obj


class Swarm(object):
    """An environment in which a population of Particles evolves.
    """

    def __init__(self, seed_num: int, num_particles: int, num_srvs: int, num_exp=10):
        """Creates a Swarm object.

        Args:
            seed_num: The Experiments seed.
            num_particles: The Particles count within the Swarm.
            num_srvs: The total servers count.
            num_exp: The total count of experiments.
        """
        assert num_particles > 1, "The number of particles must be greater than 1"
        seed(seed_num)
        self.seed = seed_num  #: The Experiments' seed.
        self.population = [
            Particle(SchedulerConfig.random()) for _ in range(num_particles)
        ]  #: list of Particle objects: A container for the members of the the Swarm.
        self.num_srvs = num_srvs  #: The total servers count.
        self.num_exp = num_exp  #: The total count of experiments.
        self.best_particle = None
        """Particle: The Particle with lowest cost in the Swarm."""
        self.experiment = Experiments()  #: Experiments: The experimental environment.
        self.logger = structlog.getLogger(__name__)  #: The Swarm's logger.

    def run_epochs(self, num_epochs: int, stat_handler):
        """Runs the experiments for the specified number of epochs.

        Args:
            num_epochs: The epoch count to be run.
            stat_handler: A method handler for injecting a drawing function \
            (draw_stats).

        Returns:
            list: A list of EpochCost objects encapsulating all costs resulting \
            from each epochs runs.
        """
        epochs_costs = []
        for i in range(num_epochs):
            self.logger.info("running epoch", epoch=f"{i+1}/{num_epochs}")
            epoch_cost = self._run_epoch(i, stat_handler)
            epochs_costs.append(epoch_cost)
        return epochs_costs

    def _run_epoch(self, num_epoch: int, stat_handler):
        """Runs the experiments for one epoch.

        Args:
            num_epoch: The epoch identifier.
            stat_handler: A method handler for injecting a drawing function \
            (draw_stats).

        Returns:
            EpochCost: An EpochCost object encapsulating all costs resulting from the each run.
        """
        particles_cost = []
        best_cost = None
        for i, particle in enumerate(self.population):
            self.logger.info(
                "running experiments",
                particle=f"{i+1}/{len(self.population)}",
                epoch=num_epoch + 1,
            )
            stats = self.experiment.run_expts(
                particle.config,
                num_srvs=self.num_srvs,
                num_expts=self.num_exp,
                seed_num=num_epoch,
            )

            if stat_handler is not None:
                stat_handler(num_epoch, i, stats)

            cost = mean([stat.cost for stat in stats])
            particles_cost.append(cost)
            if best_cost is None or cost < best_cost:
                best_cost = cost
                self.best_particle = particle
            particle.update_cost(cost)

        for particle in self.population:
            particle.update_position(self.best_particle.config)

        return EpochCost.from_costs(num_epoch, particles_cost)
