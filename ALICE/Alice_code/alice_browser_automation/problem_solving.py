"""
Problem Solving Action Suite for Alice Browser Automation.

This module implements the Problem Solving Action Suite that handles:
- Web research for desktop problem solutions
- Solution extraction from search results
- Integration with Open Interpreter for command execution
- Solution verification and reporting

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from alice_browser_automation.types import (
    BrowserTask, TaskResult, BrowserSession, TaskType,
    BrowserAction, ActionType, ElementSelectors
)
from alice_browser_automation.exceptions import BrowserAutomationError


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class SolutionSource(Enum):
    """Sources of solutions."""
    STACKOVERFLOW = "stackoverflow"
    GITHUB = "github"
    DOCUMENTATION = "documentation"
    FORUM = "forum"
    BLOG = "blog"
    OTHER = "other"


@dataclass
class Solution:
    """
    Represents a potential solution to a problem.
    """
    solution_id: str
    title: str
    description: str
    steps: List[str]
    source_url: str
    source_type: SolutionSource
    relevance_score: float  # 0.0 to 1.0
    commands: Optional[List[str]] = None  # Commands to execute
    requires_approval: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "solution_id": self.solution_id,
            "title": self.title,
            "description": self.description,
            "steps": self.steps,
            "source_url": self.source_url,
            "source_type": self.source_type.value,
            "relevance_score": self.relevance_score,
            "commands": self.commands,
            "requires_approval": self.requires_approval
        }


@dataclass
class ExecutionResult:
    """
    Result of executing a solution.
    """
    solution_id: str
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    verified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "solution_id": self.solution_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_seconds": self.execution_time_seconds,
            "verified": self.verified
        }


@dataclass
class ProblemContext:
    """
    Context information about the problem.
    """
    problem_description: str
    system_info: Optional[Dict[str, Any]] = None
    error_messages: Optional[List[str]] = None
    attempted_solutions: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "problem_description": self.problem_description,
            "system_info": self.system_info or {},
            "error_messages": self.error_messages or [],
            "attempted_solutions": self.attempted_solutions or []
        }


# ============================================================================
# Problem Solving Action Suite
# ============================================================================

class ProblemSolvingActionSuite:
    """
    Problem Solving Action Suite for browser automation.
    
    Handles desktop problem solving through web research, solution extraction,
    and integration with Open Interpreter for command execution.
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """
    
    def __init__(
        self,
        engine: Any,  # BrowserAutomationEngine (avoid circular import)
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Problem Solving Action Suite.
        
        Args:
            engine: BrowserAutomationEngine instance
            config: Optional configuration dictionary
        """
        self.engine = engine
        self.config = config or {}
        
        # Default search engines and resources
        self.search_engines = self.config.get("search_engines", {
            "google": "https://www.google.com/search?q=",
            "stackoverflow": "https://stackoverflow.com/search?q=",
            "github": "https://github.com/search?q="
        })
        
        # Solution ranking weights
        self.ranking_weights = self.config.get("ranking_weights", {
            "source_reputation": 0.3,
            "content_relevance": 0.4,
            "recency": 0.2,
            "community_votes": 0.1
        })
        
        # Open Interpreter integration (will be initialized when needed)
        self.open_interpreter_available = False
        self.open_interpreter = None
        
        logger.info("Problem Solving Action Suite initialized")
    
    # ========================================================================
    # Main Problem Solving Method
    # ========================================================================
    
    async def solve_problem(
        self,
        problem_description: str,
        system_info: Optional[Dict[str, Any]] = None,
        max_solutions: int = 5,
        auto_execute: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> TaskResult:
        """
        Solve a desktop problem using web research and command execution.
        
        Workflow:
        1. Search for solutions using web search
        2. Extract and parse solution steps
        3. Rank solutions by relevance
        4. Present solutions to user
        5. Execute approved solution (if auto_execute or user approves)
        6. Verify solution effectiveness
        7. Report results
        
        Args:
            problem_description: Description of the problem
            system_info: Optional system information context
            max_solutions: Maximum number of solutions to find
            auto_execute: Whether to auto-execute top solution (requires approval)
            progress_callback: Optional callback for progress updates
        
        Returns:
            TaskResult with solutions and execution results
        
        Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
        """
        logger.info(f"Starting problem solving: {problem_description}")
        
        try:
            # Create problem context
            context = ProblemContext(
                problem_description=problem_description,
                system_info=system_info
            )
            
            # Step 1: Search for solutions
            if progress_callback:
                progress_callback("Searching for solutions...")
            
            solutions = await self.search_solutions(
                context=context,
                max_results=max_solutions,
                progress_callback=progress_callback
            )
            
            if not solutions:
                return TaskResult(
                    task_id=f"problem_solving_{datetime.now().timestamp()}",
                    success=False,
                    summary="No solutions found",
                    actions_taken=["search"],
                    extracted_data={"solutions": []},
                    error="No solutions found for the problem",
                    duration_seconds=0.0
                )
            
            # Step 2: Rank solutions
            if progress_callback:
                progress_callback(f"Found {len(solutions)} solutions, ranking...")
            
            ranked_solutions = self._rank_solutions(solutions)
            
            # Step 3: Present solutions
            solutions_data = [sol.to_dict() for sol in ranked_solutions]
            
            # Step 4: Execute solution if approved
            execution_results = []
            if auto_execute and ranked_solutions:
                if progress_callback:
                    progress_callback("Executing top solution...")
                
                top_solution = ranked_solutions[0]
                exec_result = await self.execute_solution(
                    solution=top_solution,
                    progress_callback=progress_callback
                )
                execution_results.append(exec_result.to_dict())
            
            # Create task result
            result = TaskResult(
                task_id=f"problem_solving_{datetime.now().timestamp()}",
                success=True,
                summary=f"Found {len(solutions)} solutions for: {problem_description}",
                actions_taken=["search", "extract", "rank"],
                extracted_data={
                    "solutions": solutions_data,
                    "execution_results": execution_results,
                    "top_solution": ranked_solutions[0].to_dict() if ranked_solutions else None
                },
                error="",
                duration_seconds=0.0
            )
            
            logger.info(f"Problem solving completed: {len(solutions)} solutions found")
            return result
            
        except Exception as e:
            logger.error(f"Problem solving failed: {e}")
            return TaskResult(
                task_id=f"problem_solving_{datetime.now().timestamp()}",
                success=False,
                summary=f"Problem solving failed: {str(e)}",
                actions_taken=[],
                extracted_data={},
                error=str(e),
                duration_seconds=0.0
            )
    
    # ========================================================================
    # Solution Search
    # ========================================================================
    
    async def search_solutions(
        self,
        context: ProblemContext,
        max_results: int = 5,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Solution]:
        """
        Search for solutions using web search.
        
        Searches multiple sources:
        - Google search
        - Stack Overflow
        - GitHub issues
        - Documentation sites
        
        Args:
            context: Problem context
            max_results: Maximum number of solutions to return
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of Solution objects
        
        Requirements: 6.1, 6.2
        """
        logger.info(f"Searching for solutions: {context.problem_description}")
        
        try:
            # Create search query
            search_query = self._build_search_query(context)
            
            # Create browser task for web search
            task = BrowserTask(
                task_id=f"search_{datetime.now().timestamp()}",
                description=f"Search for solutions: {search_query}",
                task_type=TaskType.PROBLEM_SOLVING,
                parameters={
                    "query": search_query,
                    "max_results": max_results,
                    "sources": list(self.search_engines.keys())
                },
                target_url=self.search_engines["google"] + search_query,
                expected_outcome="Solutions found and extracted"
            )
            
            # Execute search through engine
            result = await self.engine.execute_task(
                task_description=task.description,
                task_type=task.task_type,
                parameters=task.parameters,
                target_url=task.target_url,
                progress_callback=progress_callback
            )
            
            # Extract solutions from results
            solutions = self._extract_solutions_from_results(result)
            
            logger.info(f"Found {len(solutions)} solutions")
            return solutions
            
        except Exception as e:
            logger.error(f"Solution search failed: {e}")
            return []
    
    async def extract_solution_steps(
        self,
        solution_url: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[Solution]:
        """
        Extract solution steps from a specific page.
        
        Args:
            solution_url: URL of the solution page
            progress_callback: Optional callback for progress updates
        
        Returns:
            Solution object or None if extraction fails
        
        Requirements: 6.2, 6.4
        """
        logger.info(f"Extracting solution from: {solution_url}")
        
        try:
            # Create browser task for extraction
            task = BrowserTask(
                task_id=f"extract_{datetime.now().timestamp()}",
                description=f"Extract solution from {solution_url}",
                task_type=TaskType.PROBLEM_SOLVING,
                parameters={"extract_steps": True, "extract_commands": True},
                target_url=solution_url,
                expected_outcome="Solution steps extracted"
            )
            
            # Execute extraction through engine
            result = await self.engine.execute_task(
                task_description=task.description,
                task_type=task.task_type,
                parameters=task.parameters,
                target_url=task.target_url,
                progress_callback=progress_callback
            )
            
            # Parse extracted data into Solution
            if result.success and result.extracted_data:
                solution = self._parse_solution_data(result.extracted_data, solution_url)
                return solution
            
            return None
            
        except Exception as e:
            logger.error(f"Solution extraction failed: {e}")
            return None
    
    # ========================================================================
    # Solution Execution (Open Interpreter Integration)
    # ========================================================================
    
    async def execute_solution(
        self,
        solution: Solution,
        require_approval: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> ExecutionResult:
        """
        Execute a solution using Open Interpreter.
        
        Args:
            solution: Solution to execute
            require_approval: Whether to require user approval
            progress_callback: Optional callback for progress updates
        
        Returns:
            ExecutionResult with execution details
        
        Requirements: 6.3, 6.5
        """
        logger.info(f"Executing solution: {solution.solution_id}")
        
        try:
            # Check if Open Interpreter is available
            if not self._check_open_interpreter():
                return ExecutionResult(
                    solution_id=solution.solution_id,
                    success=False,
                    output="",
                    error="Open Interpreter not available",
                    execution_time_seconds=0.0
                )
            
            # Require approval if needed
            if require_approval and solution.requires_approval:
                if progress_callback:
                    progress_callback(f"Solution requires approval: {solution.title}")
                
                # In real implementation, this would prompt user via voice
                # For now, we'll simulate approval
                approved = True  # TODO: Implement actual approval mechanism
                
                if not approved:
                    return ExecutionResult(
                        solution_id=solution.solution_id,
                        success=False,
                        output="",
                        error="Solution execution not approved by user",
                        execution_time_seconds=0.0
                    )
            
            # Execute commands
            if progress_callback:
                progress_callback("Executing solution commands...")
            
            start_time = datetime.now()
            output_lines = []
            
            if solution.commands:
                for cmd in solution.commands:
                    if progress_callback:
                        progress_callback(f"Executing: {cmd}")
                    
                    # Execute command via Open Interpreter
                    cmd_result = await self._execute_command(cmd)
                    output_lines.append(f"$ {cmd}")
                    output_lines.append(cmd_result)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Verify solution
            verified = await self._verify_solution(solution)
            
            result = ExecutionResult(
                solution_id=solution.solution_id,
                success=True,
                output="\n".join(output_lines),
                error="",
                execution_time_seconds=execution_time,
                verified=verified
            )
            
            logger.info(f"Solution executed successfully: {solution.solution_id}")
            return result
            
        except Exception as e:
            logger.error(f"Solution execution failed: {e}")
            return ExecutionResult(
                solution_id=solution.solution_id,
                success=False,
                output="",
                error=str(e),
                execution_time_seconds=0.0
            )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _build_search_query(self, context: ProblemContext) -> str:
        """Build optimized search query from problem context."""
        query_parts = [context.problem_description]
        
        if context.error_messages:
            # Add first error message to query
            query_parts.append(context.error_messages[0])
        
        if context.system_info:
            # Add OS info if available
            if "os" in context.system_info:
                query_parts.append(context.system_info["os"])
        
        return " ".join(query_parts)
    
    def _extract_solutions_from_results(self, result: TaskResult) -> List[Solution]:
        """Extract Solution objects from search results."""
        solutions = []
        
        # Parse extracted data
        if result.extracted_data and "solutions" in result.extracted_data:
            for sol_data in result.extracted_data["solutions"]:
                solution = Solution(
                    solution_id=sol_data.get("id", f"sol_{len(solutions)}"),
                    title=sol_data.get("title", ""),
                    description=sol_data.get("description", ""),
                    steps=sol_data.get("steps", []),
                    source_url=sol_data.get("url", ""),
                    source_type=self._detect_source_type(sol_data.get("url", "")),
                    relevance_score=sol_data.get("relevance", 0.5),
                    commands=sol_data.get("commands")
                )
                solutions.append(solution)
        
        return solutions
    
    def _detect_source_type(self, url: str) -> SolutionSource:
        """Detect source type from URL."""
        url_lower = url.lower()
        
        if "stackoverflow.com" in url_lower:
            return SolutionSource.STACKOVERFLOW
        elif "github.com" in url_lower:
            return SolutionSource.GITHUB
        elif "docs." in url_lower or "documentation" in url_lower:
            return SolutionSource.DOCUMENTATION
        elif "forum" in url_lower:
            return SolutionSource.FORUM
        elif "blog" in url_lower:
            return SolutionSource.BLOG
        else:
            return SolutionSource.OTHER
    
    def _rank_solutions(self, solutions: List[Solution]) -> List[Solution]:
        """
        Rank solutions by relevance.
        
        Requirements: 6.4
        """
        # Sort by relevance score (descending)
        ranked = sorted(solutions, key=lambda s: s.relevance_score, reverse=True)
        return ranked
    
    def _parse_solution_data(self, data: Dict[str, Any], url: str) -> Solution:
        """Parse extracted data into Solution object."""
        return Solution(
            solution_id=data.get("id", f"sol_{datetime.now().timestamp()}"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            steps=data.get("steps", []),
            source_url=url,
            source_type=self._detect_source_type(url),
            relevance_score=data.get("relevance", 0.5),
            commands=data.get("commands")
        )
    
    def _check_open_interpreter(self) -> bool:
        """Check if Open Interpreter is available."""
        # TODO: Implement actual Open Interpreter check
        # For now, return False as it's not integrated yet
        return False
    
    async def _execute_command(self, command: str) -> str:
        """Execute a command via Open Interpreter."""
        # TODO: Implement actual Open Interpreter execution
        # For now, return simulated output
        return f"[Simulated] Command executed: {command}"
    
    async def _verify_solution(self, solution: Solution) -> bool:
        """
        Verify if solution was effective.
        
        Requirements: 6.6
        """
        # TODO: Implement actual verification logic
        # This would check if the problem is resolved
        return True
    
    def get_supported_sources(self) -> List[str]:
        """Get list of supported solution sources."""
        return list(self.search_engines.keys())
